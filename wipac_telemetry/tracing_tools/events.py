"""Tools for working with events."""


from functools import wraps
from typing import Any, Callable, List, Optional

from opentelemetry.util import types

from .utils import (
    LOGGER,
    FunctionInspection,
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
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            event_name = name if name else func.__qualname__  # Ex: MyObj.method
            func_inspect = FunctionInspection(func, args, kwargs)
            _attrs = wrangle_attributes(attributes, func_inspect, all_args, these)

            if span:
                override_span = func_inspect.rget(span, Span)
                override_span.add_event(event_name, attributes=_attrs)
                LOGGER.debug(
                    f"Recorded event `{event_name}` for span `{override_span.name}` with: "
                    f"attributes={list(_attrs.keys()) if _attrs else []}"
                )
            else:
                if not get_current_span().is_recording():
                    raise RuntimeError("There is no currently recording span context.")
                get_current_span().add_event(event_name, attributes=_attrs)
                LOGGER.debug(
                    f"Recorded event `{event_name}` for span `{get_current_span().name}` with: "  # type: ignore[attr-defined]
                    f"attributes={list(_attrs.keys()) if _attrs else []}"
                )

            return func(*args, **kwargs)

        return wrapper

    return inner_function


def add_event(name: str, attributes: types.Attributes = None) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, attributes=attributes)
