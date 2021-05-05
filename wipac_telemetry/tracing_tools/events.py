"""Tools for working with events."""


import asyncio
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple

from opentelemetry.util import types

from .utils import (
    LOGGER,
    Args,
    FunctionInspection,
    Kwargs,
    Span,
    get_current_span,
    wrangle_attributes,
)


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
        event_name -- name of event; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to event
        all_args -- whether to auto-add all the function's arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        span -- the variable name of the span instance to add event to (defaults to current span)

    Raises a `RuntimeError` if no current span is recording.
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Tuple[Span, str, Kwargs]:
            event_name = name if name else func.__qualname__  # Ex: MyObj.method
            func_inspect = FunctionInspection(func, args, kwargs)
            _attrs = wrangle_attributes(attributes, func_inspect, all_args, these)

            if span:
                _span = func_inspect.rget(span, Span)
            else:
                if not get_current_span().is_recording():
                    raise RuntimeError("There is no currently recording span context.")
                _span = get_current_span()

            LOGGER.debug(
                f"Recorded event `{event_name}` for span `{_span.name}` with: "
                f"attributes={list(_attrs.keys()) if _attrs else []}"
            )

            return _span, event_name, {"attributes": _attrs}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _span, event_name, setup_kwargs = setup(args, kwargs)
            _span.add_event(event_name, **setup_kwargs)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _span, event_name, setup_kwargs = setup(args, kwargs)
            _span.add_event(event_name, **setup_kwargs)
            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper

    return inner_function


def add_event(name: str, attributes: types.Attributes = None) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, attributes=attributes)
