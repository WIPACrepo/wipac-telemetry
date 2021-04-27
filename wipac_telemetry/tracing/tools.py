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


LOGGER = logging.getLogger("wipac-telemetry")

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

    def sig_values(self) -> Dict[str, Any]:
        """Return signature-values as a `dict`."""
        return self._dict

    def self_values(self) -> Dict[str, Any]:
        """Return bound-instance's values as a `dict`."""
        try:
            return self.func.__self__.__dict__  # type: ignore[attr-defined, no-any-return]
        except AttributeError:
            LOGGER.warning(
                "Attempted to access bound-instance values from non-method object."
            )
            return {}

    def get_value(self, location: str) -> Any:
        """Retrieve the value from the symbol called `location`.

        Accepts signature- and `self.*`-values.

        Raises:
            KeyError -- if location is not found
        """
        if location.startswith("self."):
            self_location = location.lstrip("self.")
            return self.self_values()[self_location]
        else:
            return self.sig_values()[location]


def _wrangle_attributes(
    attributes: types.Attributes,
    func_inspect: _FunctionInspection,
    all_args: bool,
    these: Optional[List[str]],
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

    if these:
        raw.update({a: func_inspect.get_value(a) for a in these})

    if all_args:
        raw.update(func_inspect.sig_values())

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
    all_args: bool = False,
    these: Optional[List[str]] = None,
    inject: bool = False,
    parent: str = "",
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Wraps a `tracer.start_as_current_span()` context.

    Keyword Arguments:
        name -- name of span; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        inject -- whether to inject the span instance into the function (as `span`).
                  *`inject=True` won't set as current span nor automatically exit once function is done.*
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = name if name else func.__qualname__  # Ex: MyClass.method
            tracer_name = inspect.getfile(func)  # Ex: /path/to/source_file.py

            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, all_args, these)

            LOGGER.debug(
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
    all_args: bool = False,
    these: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Decorate to trace a function as a new event.

    The event is added under the current context's span.

    Keyword Arguments:
        event_name -- name of event; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to event
        all_args -- whether to auto-add all the function's arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            event_name = name if name else func.__qualname__  # Ex: MyObj.method

            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, all_args, these)

            LOGGER.debug(
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
