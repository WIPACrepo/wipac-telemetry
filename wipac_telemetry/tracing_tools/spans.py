"""Tools for working with spans."""


import asyncio
import inspect
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, List, Optional, TypedDict

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.util import types

from .utils import (
    LOGGER,
    Args,
    FunctionInspector,
    Kwargs,
    Link,
    Span,
    SpanKind,
    convert_to_attributes,
)

########################################################################################


class SpanBehavior(Enum):
    """Enum for indicating type of span behavior is wanted."""

    CURRENT_END_ON_EXIT = auto()
    CURRENT_LEAVE_OPEN_ON_EXIT = auto()
    INDEPENDENT_SPAN = auto()


class InvalidSpanBehaviorValue(ValueError):
    """Raise when an invalid SpanBehvior value is attempted."""


########################################################################################


class _OTELAttributeSettings(TypedDict):
    attributes: types.Attributes
    all_args: bool
    these: List[str]


########################################################################################


class _NewSpanSettings(TypedDict):
    name: str
    links: List[str]
    kind: SpanKind


class _ReuseSpanSettings(TypedDict):
    span_var_name: str


########################################################################################


class _SpanConductor:
    def __init__(
        self,
        func: Callable[..., Any],
        otel_attrs_settings: _OTELAttributeSettings,
        args: Args,
        kwargs: Kwargs,
    ):
        self.inspector = FunctionInspector(func, args, kwargs)
        self.otel_attributes = self.inspector.wrangle_otel_attributes(
            otel_attrs_settings["all_args"],
            otel_attrs_settings["these"],
            otel_attrs_settings["attributes"],
        )

    def new_span(self, settings: _NewSpanSettings, is_independent: bool) -> Span:
        """Set up, start, and return a new span instance."""
        if settings["name"]:
            span_name = settings["name"]
        else:
            span_name = self.inspector.func.__qualname__  # Ex: MyClass.method

        tracer_name = inspect.getfile(self.inspector.func)  # Ex: /path/to/file.py

        if is_independent and "span" in settings["links"]:  # TODO - is this necessary?
            raise ValueError("Cannot self-link the independent/injected span: `span`")

        if settings["kind"] == SpanKind.SERVER:
            context = extract(self.inspector.resolve_attr("self.request.headers"))
        else:
            context = None  # `None` will default to current context

        _links = self.inspector.get_links(settings["links"])

        tracer = trace.get_tracer(tracer_name)
        span = tracer.start_span(
            span_name,
            context=context,
            kind=settings["kind"],
            attributes=self.otel_attributes,
            links=_links,
        )

        LOGGER.info(
            f"Started span `{span_name}` for tracer `{tracer_name}` with: "
            f"attributes={list(self.otel_attributes.keys()) if self.otel_attributes else []}, "
            f"links={[k.context for k in _links]}"
        )

        return span

    def reuse_span(self, settings: _ReuseSpanSettings) -> Span:
        """Find, supplement, and return an exiting span instance."""
        span = self.inspector.get_span(settings["span_var_name"])

        if self.otel_attributes:
            for key, value in self.otel_attributes.items():
                span.set_attribute(key, value)  # TODO - check for duplicates

        LOGGER.info(
            f"Re-using span `{span.name}` (from '{settings['span_var_name']}') with: "
            f"additional attributes={list(self.otel_attributes.keys()) if self.otel_attributes else []}"
        )

        return span


########################################################################################


def _spanned(
    otel_attrs_settings: _OTELAttributeSettings,
    new_span_settings: Optional[_NewSpanSettings],
    reuse_span_settings: Optional[_ReuseSpanSettings],
    behavior: SpanBehavior,
) -> Callable[..., Any]:
    """Handle decorating a function with either a new span or a reused span."""

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Span:
            setup = _SpanConductor(func, otel_attrs_settings, args, kwargs)
            if new_span_settings:
                is_independent = behavior == SpanBehavior.INDEPENDENT_SPAN
                return setup.new_span(new_span_settings, is_independent)
            elif reuse_span_settings:
                return setup.reuse_span(reuse_span_settings)
            else:
                raise Exception("Undefined spanning setup.")

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Function")
            span = setup(args, kwargs)

            if behavior == SpanBehavior.INDEPENDENT_SPAN:
                kwargs["span"] = span
                return func(*args, **kwargs)
            elif behavior == SpanBehavior.CURRENT_END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    return func(*args, **kwargs)
            elif behavior == SpanBehavior.CURRENT_LEAVE_OPEN_ON_EXIT:
                with trace.use_span(span, end_on_exit=False):
                    return func(*args, **kwargs)
            else:
                raise InvalidSpanBehaviorValue(behavior)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Generator Function")
            span = setup(args, kwargs)

            if behavior == SpanBehavior.INDEPENDENT_SPAN:
                kwargs["span"] = span
                for val in func(*args, **kwargs):
                    yield val
            elif behavior == SpanBehavior.CURRENT_END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    for val in func(*args, **kwargs):
                        yield val
            elif behavior == SpanBehavior.CURRENT_LEAVE_OPEN_ON_EXIT:
                with trace.use_span(span, end_on_exit=False):
                    for val in func(*args, **kwargs):
                        yield val
            else:
                raise InvalidSpanBehaviorValue(behavior)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Async Function")
            span = setup(args, kwargs)

            if behavior == SpanBehavior.INDEPENDENT_SPAN:
                kwargs["span"] = span
                return await func(*args, **kwargs)
            elif behavior == SpanBehavior.CURRENT_END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    return await func(*args, **kwargs)
            elif behavior == SpanBehavior.CURRENT_LEAVE_OPEN_ON_EXIT:
                with trace.use_span(span, end_on_exit=False):
                    return await func(*args, **kwargs)
            else:
                raise InvalidSpanBehaviorValue(behavior)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            if inspect.isgeneratorfunction(func):
                return gen_wrapper
            else:
                return wrapper

    return inner_function


########################################################################################


def spanned(
    name: Optional[str] = None,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
    behavior: SpanBehavior = SpanBehavior.CURRENT_END_ON_EXIT,
    links: Optional[List[str]] = None,
    kind: SpanKind = SpanKind.INTERNAL,
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Wraps a `tracer.start_as_current_span()` context.

    Keyword Arguments:
        name -- name of span; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        behavior -- TODO indicate what type of span behavior is wanted:
                    - `SpanBehavior.AUTO_CURRENT_SPAN`
                        + start span as the current span (accessible via `get_current_span()`)
                        + automatically exit after function returns
                        + default value
                    - `SpanBehavior.INDEPENDENT_SPAN`
                        + start span NOT as the current span
                        + injects span instance into the function/method's argument list as `span`
                        + requires a call to `span.end()` to send traces
                        + can be persisted between independent functions
        links -- a list of variable names of `Link` instances (span-links) - useful for cross-process tracing
        kind -- a `SpanKind` enum value
                - ``SpanKind.INTERNAL` - (default) normal, in-application spans
                - `SpanKind.CLIENT` - spanned function makes outgoing cross-service requests
                - `SpanKind.SERVER` - spanned function handles incoming cross-service requests
                    * contextually connected to a client-service's span via parent pointer
                    * (looks at `self.request` instance for necessary info)
                - `SpanKind.CONSUMER` - spanned function makes outgoing cross-service messages
                - `SpanKind.PRODUCER` - spanned function handles incoming cross-service messages

    Raises a `ValueError` when attempting to self-link the independent/injected span
    Raises a `InvalidSpanBehaviorValue` when an invalid `behavior` value is attempted
    """
    if not these:
        these = []
    if not name:
        name = ""
    if not links:
        links = []

    return _spanned(
        {"attributes": attributes, "all_args": all_args, "these": these},
        {"name": name, "links": links, "kind": kind},
        None,
        behavior,
    )


def respanned(
    span_var_name: str,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
    behavior: SpanBehavior = SpanBehavior.CURRENT_END_ON_EXIT,
) -> Callable[..., Any]:
    """Decorate to trace a function with an existing span.

    Wraps a `use_span()` context.

    Arguments:
        span_var_name -- name of span variable

    Keyword Arguments:
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        behavior -- TODO indicate what type of span behavior is wanted:
                    - `SpanBehavior.AUTO_CURRENT_SPAN`
                        + start span as the current span (accessible via `get_current_span()`)
                        + automatically exit after function returns
                        + default value
                    - `SpanBehavior.INDEPENDENT_SPAN`
                        + start span NOT as the current span
                        + injects span instance into the function/method's argument list as `span`
                        + requires a call to `span.end()` to send traces
                        + can be persisted between independent functions

    Raises a `InvalidSpanBehaviorValue` when an invalid `behavior` value is attempted
    """
    if not these:
        these = []

    return _spanned(
        {"attributes": attributes, "all_args": all_args, "these": these},
        None,
        {"span_var_name": span_var_name},
        behavior,
    )


########################################################################################

# TODO - figure out what to do with linking


def make_link(
    span: Span, purpose: str, other_attributes: types.Attributes = None
) -> Link:
    """Make a Link for a Span (context) with a collection of attributes."""
    attrs = dict(other_attributes) if other_attributes else {}
    attrs["purpose"] = purpose

    return Link(span.get_span_context(), attributes=convert_to_attributes(attrs))
