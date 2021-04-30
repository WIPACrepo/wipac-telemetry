"""Common tools for interacting with the OpenTelemetry Tracing API."""


import copy
import inspect
import logging
from collections.abc import Sequence
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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
Link = trace.Link


class _FunctionInspection:
    """A wrapper around a function and its introspection functionalities."""

    def __init__(self, func: Callable[..., Any], args: Args, kwargs: Kwargs):
        bound_args = inspect.signature(func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        self.param_args = dict(bound_args.arguments)

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def rget(
        self, var_name: str, typ: Union[None, type, Tuple[type, ...]] = None
    ) -> Any:
        """Retrieve the instance at `var_name` from signature-parameter args.

        Optionally, check if the value is of type(s), `type`.

        Searches:
            - non-callable objects
            - supports nested/chained attributes (including `self.*` attributes)

        Examples:
            signature -> (self, foo)
            variable names -> self.green, foo, foo.bar.baz

        Raises:
            AttributeError -- if var_name is not found
            TypeError -- if the instance is found, but isn't of the type(s) indicated
        """

        def dot_left(string: str) -> str:
            return string.split(".", maxsplit=1)[0]

        def dot_right(string: str) -> str:
            try:
                return string.split(".", maxsplit=1)[1]
            except IndexError:
                return ""

        def _rget(obj: Any, attr: str) -> Any:
            if not attr:
                return obj
            elif "." in attr:
                return _rget(getattr(obj, dot_left(attr)), dot_right(attr))
            else:
                return getattr(obj, attr)

        try:
            obj = _rget(self.param_args[dot_left(var_name)], dot_right(var_name))
        except AttributeError as e:
            raise AttributeError(  # pylint: disable=W0707
                f"'{var_name}': {e} "
                f"(present parameter arguments: {', '.join(self.param_args.keys())})"
            )
        except KeyError:
            raise AttributeError(  # pylint: disable=W0707
                f"'{var_name}': function parameters have no argument '{dot_left(var_name)}' "
                f"(present parameter arguments: {', '.join(self.param_args.keys())})"
            )

        if typ and not isinstance(obj, typ):
            raise TypeError(f"Instance '{var_name}' is not {typ}")
        return obj


def _convert_to_attributes(
    raw: Union[Dict[str, Any], types.Attributes]
) -> types.Attributes:
    """Convert dict to mapping of attributes (deep copy values).

    Bad values are disregarded.
    """
    if not raw:
        return {}

    skips = []
    legal_types = (str, bool, int, float)
    for attr in list(raw):
        if isinstance(raw[attr], legal_types):
            continue
        # check all members are of same (legal) type
        if isinstance(raw[attr], Sequence):
            member_types = list(set(type(m) for m in raw[attr]))  # type: ignore[union-attr]
            if len(member_types) == 1 and member_types[0] in legal_types:
                continue
        # illegal type
        skips.append(attr)

    return {k: copy.deepcopy(v) for k, v in raw.items() if k not in skips}


def _wrangle_attributes(
    attributes: types.Attributes,
    func_inspect: _FunctionInspection,
    all_args: bool,
    these: Optional[List[str]],
) -> types.Attributes:
    """Figure what attributes to use from the list and/or function args."""
    raw: Dict[str, Any] = {}

    if these:
        raw.update({a: func_inspect.rget(a) for a in these})

    if all_args:
        raw.update(func_inspect.param_args)

    if attributes:
        raw.update(attributes)

    return _convert_to_attributes(raw)


def _wrangle_links(
    func_inspect: _FunctionInspection, links: Optional[List[str]],
) -> List[Link]:
    if not links:
        return []

    out = []
    for var_name in links:
        try:
            link = func_inspect.rget(var_name, Link)
        except TypeError as e:
            LOGGER.warning(e)  # this var_name could be a None value (aka an OptSpan)
        else:
            out.append(link)

    return out


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
        links -- a list of variable names of `Link` instances (span-links) - useful for cross-process tracing

    Raises a `ValueError` when attempting to self-link the injected span.
    """
    # TODO - what is `is_remote`?
    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = name if name else func.__qualname__  # Ex: MyClass.method
            tracer_name = inspect.getfile(func)  # Ex: /path/to/source_file.py

            if inject and links and "span" in links:
                raise ValueError("Cannot self-link the injected span: `span`")

            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, all_args, these)
            _links = _wrangle_links(func_inspect, links)

            tracer = trace.get_tracer(tracer_name)

            LOGGER.debug(
                f"Started span `{span_name}` for tracer `{tracer_name}` with: "
                f"attributes={list(_attrs.keys()) if _attrs else []}, "
                f"links={[k.context for k in _links]}"
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
        span -- the variable name of the span instance to add event to (defaults to current span)

    Raises a `RuntimeError` if no current span is recording.
    """

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            event_name = name if name else func.__qualname__  # Ex: MyObj.method
            func_inspect = _FunctionInspection(func, args, kwargs)
            _attrs = _wrangle_attributes(attributes, func_inspect, all_args, these)

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


def make_link(span: Span, attributes: types.Attributes = None) -> Link:
    """Make a Link for a Span (context) with a collection of attributes."""
    return Link(span.get_span_context(), attributes=_convert_to_attributes(attributes))
