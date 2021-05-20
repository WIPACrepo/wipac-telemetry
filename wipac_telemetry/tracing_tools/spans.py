"""Tools for working with spans."""


import asyncio
import inspect
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Final, List, Optional, TypedDict

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
    get_current_span,
)

########################################################################################


class SpanBehavior(Enum):
    """Enum for indicating type of span behavior is wanted."""

    END_ON_EXIT = auto()
    DONT_END = auto()
    ONLY_END_ON_EXCEPTION = auto()


class InvalidSpanBehavior(ValueError):
    """Raise when an invalid SpanBehavior value is attempted."""


########################################################################################


class _OTELAttributeSettings(TypedDict):
    attributes: types.Attributes
    all_args: bool
    these: List[str]


########################################################################################


class _SpanConductor:
    """Conduct necessary processes for Span-availability."""

    def __init__(
        self, otel_attrs_settings: _OTELAttributeSettings, autoevent_reason: str
    ):
        self.otel_attrs_settings = otel_attrs_settings
        self._autoevent_reason_value: Final = autoevent_reason

    def get_span(self, inspector: FunctionInspector) -> Span:
        """Get a span, configure according to sub-class."""
        raise NotImplementedError()

    def auto_event_attrs(self, span_attrs: types.Attributes) -> types.Attributes:
        """Get the event attributes for auto-eventing a span."""
        return {
            "spanned_reason": self._autoevent_reason_value,
            "added_attributes": list(span_attrs.keys()) if span_attrs else [],
        }


class _NewSpanConductor(_SpanConductor):
    """Conduct necessary processes for making a new Span available."""

    def __init__(
        self,
        otel_attrs_settings: _OTELAttributeSettings,
        name: str,
        links: List[str],
        kind: SpanKind,
    ):
        super().__init__(otel_attrs_settings, "premiere")
        self.name = name
        self.links = links
        self.kind = kind

    def get_span(self, inspector: FunctionInspector) -> Span:
        """Set up, start, and return a new span instance."""
        if self.name:
            span_name = self.name
        else:
            span_name = inspector.func.__qualname__  # Ex: MyClass.method

        tracer_name = inspect.getfile(inspector.func)  # Ex: /path/to/file.py

        if self.kind == SpanKind.SERVER:
            context = extract(inspector.resolve_attr("self.request.headers"))
        else:
            context = None  # `None` will default to current context

        _links = inspector.get_links(self.links)
        attrs = inspector.wrangle_otel_attributes(
            self.otel_attrs_settings["all_args"],
            self.otel_attrs_settings["these"],
            self.otel_attrs_settings["attributes"],
        )

        tracer = trace.get_tracer(tracer_name)
        span = tracer.start_span(
            span_name, context=context, kind=self.kind, attributes=attrs, links=_links,
        )
        span.add_event(span_name, self.auto_event_attrs(attrs))

        LOGGER.info(
            f"Started span `{span_name}` for tracer `{tracer_name}` with: "
            f"attributes={list(attrs.keys()) if attrs else []}, "
            f"links={[k.context for k in _links]}"
        )

        return span


class _ReuseSpanConductor(_SpanConductor):
    """Conduct necessary processes for reusing an existing Span."""

    def __init__(
        self, otel_attrs_settings: _OTELAttributeSettings, span_var_name: Optional[str]
    ):
        super().__init__(otel_attrs_settings, "respanned")
        self.span_var_name = span_var_name

    def get_span(self, inspector: FunctionInspector) -> Span:
        """Find, supplement, and return an exiting span instance."""
        if self.span_var_name:
            span = inspector.get_span(self.span_var_name)
        else:
            span = get_current_span()

        attrs = inspector.wrangle_otel_attributes(
            self.otel_attrs_settings["all_args"],
            self.otel_attrs_settings["these"],
            self.otel_attrs_settings["attributes"],
        )
        if attrs:  # this may override existing attributes
            for key, value in attrs.items():
                span.set_attribute(key, value)

        span.add_event(inspector.func.__qualname__, self.auto_event_attrs(attrs))

        LOGGER.info(
            f"Re-using span `{span.name}` "
            f"(from '{self.span_var_name if self.span_var_name else 'current-span'}') "
            f"with: additional attributes={list(attrs.keys()) if attrs else []}"
        )

        return span


########################################################################################


def _spanned(conductor: _SpanConductor, behavior: SpanBehavior) -> Callable[..., Any]:
    """Handle decorating a function with either a new span or a reused span."""

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Span:
            if not isinstance(conductor, (_NewSpanConductor, _ReuseSpanConductor)):
                raise Exception(f"Undefined SpanConductor type: {conductor}.")
            else:
                return conductor.get_span(FunctionInspector(func, args, kwargs))

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Function")
            span = setup(args, kwargs)

            if behavior == SpanBehavior.ONLY_END_ON_EXCEPTION:
                try:
                    with trace.use_span(span, end_on_exit=False):
                        return func(*args, **kwargs)
                except:  # noqa: E722 # pylint: disable=bare-except
                    span.end()
                    raise
            elif behavior == SpanBehavior.END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    return func(*args, **kwargs)
            elif behavior == SpanBehavior.DONT_END:
                with trace.use_span(span, end_on_exit=False):
                    return func(*args, **kwargs)
            else:
                raise InvalidSpanBehavior(behavior)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Generator Function")
            span = setup(args, kwargs)

            if behavior == SpanBehavior.ONLY_END_ON_EXCEPTION:
                try:
                    with trace.use_span(span, end_on_exit=False):
                        for val in func(*args, **kwargs):
                            yield val
                except:  # noqa: E722 # pylint: disable=bare-except
                    span.end()
                    raise
            elif behavior == SpanBehavior.END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    for val in func(*args, **kwargs):
                        yield val
            elif behavior == SpanBehavior.DONT_END:
                with trace.use_span(span, end_on_exit=False):
                    for val in func(*args, **kwargs):
                        yield val
            else:
                raise InvalidSpanBehavior(behavior)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Async Function")
            span = setup(args, kwargs)

            if behavior == SpanBehavior.ONLY_END_ON_EXCEPTION:
                try:
                    with trace.use_span(span, end_on_exit=False):
                        return await func(*args, **kwargs)
                except:  # noqa: E722 # pylint: disable=bare-except
                    span.end()
                    raise
            elif behavior == SpanBehavior.END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    return await func(*args, **kwargs)
            elif behavior == SpanBehavior.DONT_END:
                with trace.use_span(span, end_on_exit=False):
                    return await func(*args, **kwargs)
            else:
                raise InvalidSpanBehavior(behavior)

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
    behavior: SpanBehavior = SpanBehavior.END_ON_EXIT,
    links: Optional[List[str]] = None,
    kind: SpanKind = SpanKind.INTERNAL,
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Also, record an event with the function's name and the names of the
    attributes added.

    Keyword Arguments:
        name -- name of span; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        behavior -- indicate what type of span behavior is wanted:
                    - `SpanBehavior.END_ON_EXIT`
                        + start span as the current span (accessible via `get_current_span()`)
                        + automatically end span (send traces) when function returns
                        + default value
                    - `SpanBehavior.DONT_END`
                        + start span as the current span (accessible via `get_current_span()`)
                        + requires a call to `span.end()` to send traces
                            - (or subsequent `@respanned()` with necessary `behavior` setting)
                        + can be persisted between independent functions
                        + use this when re-use is needed and an exception IS expected
                        + traces are sent if the function call is wrapped in a try-except
                    - `SpanBehavior.ONLY_END_ON_EXCEPTION`
                        + similar to `SpanBehavior.DONT_END` but auto-ends when an exception is raised
                        + use this when re-use is needed and an exception is NOT expected
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
    Raises a `InvalidSpanBehavior` when an invalid `behavior` value is attempted
    """
    if not these:
        these = []
    if not name:
        name = ""
    if not links:
        links = []

    return _spanned(
        _NewSpanConductor(
            {"attributes": attributes, "all_args": all_args, "these": these},
            name,
            links,
            kind,
        ),
        behavior,
    )


def respanned(
    span_var_name: Optional[str],
    behavior: SpanBehavior,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Decorate to trace a function with an existing span.

    Also, record an event with the function's name and the names of the
    attributes added.

    Arguments:
        span_var_name -- name of Span instance variable; if None (or ""), the current-span is used
        behavior -- indicate what type of span behavior is wanted:
                    - `SpanBehavior.END_ON_EXIT`
                        + start span as the current span (accessible via `get_current_span()`)
                        + automatically end span (send traces) when function returns
                        + default value
                    - `SpanBehavior.DONT_END`
                        + start span as the current span (accessible via `get_current_span()`)
                        + requires a call to `span.end()` to send traces
                            - (or subsequent `@respanned()` with necessary `behavior` setting)
                        + can be persisted between independent functions
                        + use this when re-use is needed and an exception IS expected
                        + (traces are sent if the function call is wrapped in a try-except)
                    - `SpanBehavior.ONLY_END_ON_EXCEPTION`
                        + similar to `SpanBehavior.DONT_END` but auto-ends when an exception is raised
                        + use this when re-use is needed and an exception is NOT expected

    Keyword Arguments:
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes

    Raises an `InvalidSpanBehavior` when an invalid `behavior` value is attempted
    """
    if not these:
        these = []

    return _spanned(
        _ReuseSpanConductor(
            {"attributes": attributes, "all_args": all_args, "these": these},
            span_var_name,
        ),
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
