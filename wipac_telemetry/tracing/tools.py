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
    """A wrapper around a function and its introspection functionalities."""

    def __init__(self, func: Callable[..., Any], args: Args, kwargs: Kwargs):
        self._sig_values = dict(zip(inspect.signature(func).parameters, args))
        self._sig_values.update(copy.deepcopy(kwargs))

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def sig_values(self) -> Dict[str, Any]:
        """Return signature's parameter values as a `dict`."""
        return self._sig_values

    def get_attr(self, location: str) -> Any:
        """Retrieve the value from the symbol: `location`.

        Accepts (non-callable) nested-attributes from
        signature- and `self.*`-values.

        Examples:
            foo, foo.bar.baz, self.ham

        Raises:
            KeyError -- if location is not found
        """

        def _get_attr(location: str, universe: Dict[str, Any]) -> Any:
            if "." in location:
                parent, child = location.split(".", maxsplit=1)
                return _get_attr(
                    child,
                    # grab all instance *and* class variables
                    {k: getattr(universe[parent], k) for k in dir(universe[parent])},
                )
            return universe[location]

        try:
            return _get_attr(location, self.sig_values())
        except KeyError as e:
            # pylint: disable=W0707
            raise AttributeError(f"{e} not found in '{location}'")


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
        raw.update({a: func_inspect.get_attr(a) for a in these})

    if all_args:
        raw.update(func_inspect.sig_values())

    if attributes:
        raw.update(attributes)

    return _convert_to_attributes()


def _find_span(func_inspect: _FunctionInspection, location: str) -> OptSpan:
    """Retrieve the Span instance from the symbol: `location`.

    If `location` is Falsy, return `None`.
    """
    if not location:
        return None

    def affirm_span(val: Any) -> Span:
        if isinstance(val, Span):
            return val
        raise ValueError("Object is Not a Span")

    try:
        return affirm_span(func_inspect.get_attr(location))
    except KeyError:
        LOGGER.error(f"Location Not Found: {location}")
        return None
    except ValueError:
        LOGGER.error(f"Object Is Not a Span: {location}")
        return None


def _wrangle_links(
    func_inspect: _FunctionInspection, locations: Optional[List[str]]
) -> Optional[List[trace.Link]]:
    if not locations:
        return None

    _links = []
    for loc in locations:
        span = _find_span(func_inspect, loc)
        if span:
            _links.append(trace.Link(span.get_span_context()))

    return _links


def spanned(
    name: Optional[str] = None,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
    inject: bool = False,
    links: Optional[List[str]] = None,
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
        links -- symbols/locations of spans to link to (useful for cross-process tracing)

    # TODO - add attributes to links
    """
    # TODO - test `links`
    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = name if name else func.__qualname__  # Ex: MyClass.method
            tracer_name = inspect.getfile(func)  # Ex: /path/to/source_file.py

            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, all_args, these)
            _links = _wrangle_links(func_inspect, links)

            tracer = trace.get_tracer(tracer_name)

            LOGGER.debug(
                f"Started span `{span_name}` for tracer `{tracer_name}` with: "  # type: ignore[attr-defined]
                f"attributes={list(_attrs.keys()) if _attrs else []}, "
                f"links={[f'trace:{k.trace_id} span:{k.span_id}' for k in _links] if _links else []}"
            )
            if inject:
                kwargs["span"] = tracer.start_span(
                    span_name, attributes=_attrs, links=_links
                )
                return func(*args, **kwargs)
            else:
                with tracer.start_as_current_span(
                    span_name, attributes=_attrs, links=_links
                ):
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
    span: str = "",
) -> Callable[..., Any]:
    """Decorate to trace a function as a new event.

    The event is added under the current context's span.

    Keyword Arguments:
        event_name -- name of event; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to event
        all_args -- whether to auto-add all the function's arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        span -- the symbol-location of the span to add event to (defaults to current span)
    """
    # TODO - test `span`
    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            event_name = name if name else func.__qualname__  # Ex: MyObj.method
            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, all_args, these)
            _span = _find_span(func_inspect, span)

            if _span:
                _span.add_event(event_name, attributes=_attrs)
                LOGGER.debug(
                    f"Recorded event `{event_name}` for span `{_span.name}` with: "
                    f"attributes={list(_attrs.keys()) if _attrs else []}"
                )
            else:
                if not get_current_span().is_recording():
                    raise RuntimeError("There is no currently recording span context.")
                get_current_span().add_event(event_name, attributes=_attrs)
                LOGGER.debug(
                    f"Recorded event `{event_name}` for span `{get_current_span().name}` with: "
                    f"attributes={list(_attrs.keys()) if _attrs else []}"
                )

            return func(*args, **kwargs)

        return wrapper

    return inner_function


def add_event(name: str, attributes: types.Attributes = None) -> None:
    """Add an event to the current span."""
    get_current_span().add_event(name, attributes=attributes)
