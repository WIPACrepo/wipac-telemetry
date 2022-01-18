"""Tools for working with events."""


import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple

from opentelemetry.trace import Span, get_current_span
from opentelemetry.util import types

from .utils import LOGGER, Args, FunctionInspector, Kwargs


def evented(
    name: Optional[str] = None,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
    span: str = "",
) -> Callable[..., Any]:
    """Decorate to trace a function as a new event.

    The event is added under the current context's span.

    Keyword Arguments:
        name -- name of event; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to event
        all_args -- whether to auto-add all the function's arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        span -- the variable name of the span instance to add event to (defaults to current span)

    Raises a `RuntimeError` if no current span is recording.
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Tuple[Span, str, Kwargs]:
            event_name = name if name else func.__qualname__  # Ex: MyObj.method
            func_inspect = FunctionInspector(func, args, kwargs)
            _attrs = func_inspect.wrangle_otel_attributes(all_args, these, attributes)

            if span:
                _span = func_inspect.get_span(span)
            else:
                if not get_current_span().is_recording():
                    raise RuntimeError("There is no currently recording span context.")
                _span = get_current_span()

            LOGGER.info(
                f"Recorded event `{event_name}` for span `{_span.name}` with: "  # type: ignore[attr-defined]
                f"attributes={list(_attrs.keys()) if _attrs else []}"
            )

            return _span, event_name, {"attributes": _attrs}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Evented Function")
            _span, event_name, setup_kwargs = setup(args, kwargs)
            _span.add_event(event_name, **setup_kwargs)
            return func(*args, **kwargs)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Evented Generator Function")
            _span, event_name, setup_kwargs = setup(args, kwargs)
            _span.add_event(f"{event_name}#enter", **setup_kwargs)
            for i, val in enumerate(func(*args, **kwargs)):
                _span.add_event(f"{event_name}#{i}", **setup_kwargs)
                yield val
            _span.add_event(f"{event_name}#exit", **setup_kwargs)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Evented Async Function")
            _span, event_name, setup_kwargs = setup(args, kwargs)
            _span.add_event(event_name, **setup_kwargs)
            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            if inspect.isgeneratorfunction(func):
                return gen_wrapper
            else:
                return wrapper

    return inner_function


def add_event(name: str, attributes: types.Attributes = None) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, attributes=attributes)
