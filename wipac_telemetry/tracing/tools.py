"""Common tools for interacting with the OpenTelemetry Tracing API."""


import copy
import inspect
import logging
from collections.abc import Sequence
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

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

Args = Tuple[Any, ...]
Kwargs = Dict[str, Any]

Span = trace.Span  # alias for easy importing
OptSpan = Optional[Span]  # alias used for Span-argument injection


class _FunctionInspection:
    """A wrapper around a function, its signature, and its argument values."""

    def __init__(self, func: Callable[..., Any], args: Args, kwargs: Kwargs):
        self._dict = dict(zip(inspect.signature(func).parameters, args))
        self._dict.update(copy.deepcopy(kwargs))

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def sig_vals(self) -> Dict[str, Any]:
        """Return signature-values as a `dict`."""
        return self._dict


def _wrangle_attributes(
    attributes: types.Attributes,
    func_inspect: _FunctionInspection,
    use_args: bool,
    these_args: Optional[List[str]],
) -> types.Attributes:
    """Figure what attributes to use from the list and/or function."""
    raw: Dict[str, Any] = {}

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
        raw.update(
            {k: v for k, v in func_inspect.sig_vals().items() if k in these_args}
        )
    elif use_args:
        raw.update(func_inspect.sig_vals())

    if attributes:
        raw.update(attributes)

    return _convert_to_attributes()


def _attributes_to_string(attributes: types.Attributes) -> str:
    if not attributes:
        return "None"
    return "[" + ", ".join(f"`{k}`" for k in attributes.keys()) + "]"


def spanned(
    name: Optional[str] = None,
    attributes: types.Attributes = None,
    use_args: bool = False,
    these_args: Optional[List[str]] = None,
    inject: bool = False,
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Wraps a `tracer.start_as_current_span()` context.

    Keyword Arguments:
        name -- name of span; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to span
        use_args -- whether to auto-add the arguments as attributes
        these_args -- a whitelist of arguments to add as attributes; if not given and `use_args` is True, then all arguments will be added
        inject -- whether to inject the span instance into the function (as `span`).
                  *`inject=True` won't set as current span nor automatically exit once function is done.*
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = name if name else func.__qualname__  # Ex: MyClass.method
            tracer_name = inspect.getfile(func)  # Ex: /path/to/source_file.py

            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, use_args, these_args)

            logging.getLogger(_LOGGER_NAME).debug(
                f"Started span `{span_name}` for tracer `{tracer_name}` "
                f"with these attributes: {_attributes_to_string(_attrs)}"
            )

            tracer = trace.get_tracer(tracer_name)
            if inject:
                kwargs["span"] = tracer.start_span(span_name, attributes=_attrs)
                return func(*args, **kwargs)
            else:
                with tracer.start_as_current_span(span_name, attributes=_attrs):
                    return func(*args, **kwargs)

        return wrapper

    return inner_function


def get_current_span() -> Span:
    """Get the current span instance."""
    return trace.get_current_span()


def evented(
    name: Optional[str] = None,
    attributes: types.Attributes = None,
    use_args: bool = False,
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
            event_name = name if name else func.__qualname__  # Ex: MyObj.method

            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, use_args, these_args)

            logging.getLogger(_LOGGER_NAME).debug(
                f"Recorded event `{event_name}` for span `{get_current_span().name}` "
                f"with these attributes: {_attributes_to_string(_attrs)}"
            )

            get_current_span().add_event(event_name, attributes=_attrs)
            return func(*args, **kwargs)

        return wrapper

    return inner_function


def add_event(name: str, attributes: types.Attributes = None) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, attributes=attributes)
