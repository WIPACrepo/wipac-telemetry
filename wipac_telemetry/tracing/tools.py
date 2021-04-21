"""Common tools for interacting with the OpenTelemetry Tracing API."""


import inspect
import logging
from functools import wraps
from typing import Any, Callable, Optional

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


def new_span(
    span_name: Optional[str] = None, tracer_name: Optional[str] = None
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    If `span_name` is not provided, the wrapped function's
    name will be used. If `tracer_name` is not provided,
    the wrapped function's filename will be used.

    Wraps a `tracer.start_as_current_span()` context.
    """

    def inner_function(function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _span = span_name if span_name else function.__name__
            _tracer = tracer_name if tracer_name else inspect.getfile(function)

            logging.getLogger("wipac-telemetry").debug(
                f"Started span `{_span}` for tracer `{_tracer}`"
            )

            tracer = trace.get_tracer(_tracer)
            with tracer.start_as_current_span(_span):
                return function(*args, **kwargs)

        return wrapper

    return inner_function


def get_current_span() -> trace.Span:
    """Get the current span instance."""
    return trace.get_current_span()
