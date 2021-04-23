"""Common tools for interacting with the OpenTelemetry Tracing API."""


import copy
import inspect
import logging
from collections.abc import Sequence
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
from opentelemetry.sdk.trace.export import (  # type: ignore[import]
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.util import types

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
    SimpleSpanProcessor(ConsoleSpanExporter())
)


_LOGGER_NAME = "wipac-telemetry"


def _wrangle_attributes(
    func: Callable[..., Any],
    args: Any,
    kwargs: Any,
    attributes: types.Attributes,
    use_args: bool,
    these_args: Optional[List[str]],
) -> types.Attributes:
    raw: Dict[str, Any] = {}

    def _signature_vals() -> Dict[str, Any]:
        sig_vals = dict(zip(inspect.signature(func).parameters, args))
        sig_vals.update(copy.deepcopy(kwargs))
        return sig_vals

    def _convert_to_attributes() -> types.Attributes:
        legal_types = (str, bool, int, float)
        for attr in list(raw):
            if isinstance(raw[attr], legal_types):
                continue
            # check all members are of same (legal) type
            if isinstance(raw[attr], Sequence):
                member_types = list(set(type(m) for m in raw[attr]))
                if len(member_types) == 1 and member_types[0] in legal_types:
                    continue
            # illegal type
            del raw[attr]
        return raw

    if these_args:
        raw.update({k: v for k, v in _signature_vals().items() if k in these_args})
    elif use_args:
        raw.update(_signature_vals())

    if attributes:
        raw.update(attributes)

    return _convert_to_attributes()


def _attributes_to_string(attributes: types.Attributes) -> str:
    if not attributes:
        return "None"
    return "[" + ", ".join(f"`{k}`" for k in attributes.keys()) + "]"


def spanned(
    span_name: Optional[str] = None,
    attributes: types.Attributes = None,
    use_args: bool = True,
    these_args: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Wraps a `tracer.start_as_current_span()` context.

    Keyword Arguments:
        span_name -- name of span; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to span
        use_args -- whether to auto-add the arguments as attributes
        these_args -- a whitelist of arguments to add as attributes; if not given and `use_args` is True, then all arguments will be added
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _span = span_name if span_name else func.__qualname__  # Ex: MyClass.method
            _tracer = inspect.getfile(func)  # Ex: /path/to/source_file.py
            _attrs = _wrangle_attributes(
                func, args, kwargs, attributes, use_args, these_args
            )

            logging.getLogger(_LOGGER_NAME).debug(
                f"Started span `{_span}` for tracer `{_tracer}` "
                f"with these attributes: {_attributes_to_string(_attrs)}"
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
    event_name: Optional[str] = None,
    attributes: types.Attributes = None,
    use_args: bool = True,
    these_args: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Decorate to trace a function as a new event.

    The event is added under the current context's span.

    Keyword Arguments:
        event_name -- name of event; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to event
        use_args -- whether to auto-add the arguments as attributes
        these_args -- a whitelist of arguments to add as attributes; if not given and `use_args` is True, then all arguments will be added
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _event = event_name if event_name else func.__qualname__  # Ex: MyObj.method
            _attrs = _wrangle_attributes(
                func, args, kwargs, attributes, use_args, these_args
            )

            logging.getLogger(_LOGGER_NAME).debug(
                f"Recorded event `{_event}` for span `{get_current_span().name}` "
                f"with these attributes: {_attributes_to_string(_attrs)}"
            )

            get_current_span().add_event(_event, attributes=_attrs)
            return func(*args, **kwargs)

        return wrapper

    return inner_function


def add_event(name: str, attributes: types.Attributes) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, attributes=attributes)
