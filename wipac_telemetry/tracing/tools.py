"""Common tools for interacting with the OpenTelemetry Tracing API."""


import copy
import inspect
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
from opentelemetry.sdk.trace.export import (  # type: ignore[import]
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
    SimpleSpanProcessor(ConsoleSpanExporter())
)


def _signature_vals(
    function: Callable[..., Any], args: Any, kwargs: Any
) -> Dict[str, Any]:
    sig_vals = dict(zip(inspect.signature(function).parameters, args))
    sig_vals.update(copy.deepcopy(kwargs))
    return sig_vals


def spanned(
    span_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    If `span_name` is not provided, the wrapped function's
    qualified name will be used. If `attributes` is not provided,
    the wrapped function's signature and argument values will
    be used.

    Wraps a `tracer.start_as_current_span()` context.
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _span = span_name if span_name else func.__qualname__
            _tracer = func.__module__
            _attrs = attributes if attributes else _signature_vals(func, args, kwargs)

            logging.getLogger("wipac-telemetry").debug(
                f"Started span `{_span}` for tracer `{_tracer}`"
            )

            tracer = trace.get_tracer(_tracer)
            with tracer.start_as_current_span(_span, attributes=_attrs):
                return func(*args, **kwargs)

        return wrapper

    return inner_function


def get_current_span() -> trace.Span:
    """Get the current span instance."""
    return trace.get_current_span()


def evented(
    event_name: Optional[str] = None, body: Optional[Dict[str, Any]] = None
) -> Callable[..., Any]:
    """Decorate to trace a function as a new event.

    The event is added under the current context's span.

    If `event_name` is not provided, the wrapped function's
    qualified name will be used. If `body` is not provided,
    the wrapped function's signature and argument values will
    be used.
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _event = event_name if event_name else func.__qualname__
            _body = body if body else _signature_vals(func, args, kwargs)

            logging.getLogger("wipac-telemetry").debug(
                f"Recorded event `{_event}` for span `{get_current_span()}`"
            )

            get_current_span().add_event(_event, _body)
            return func(*args, **kwargs)

        return wrapper

    return inner_function


def add_event(name: str, body: Dict[str, Any]) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, body)
