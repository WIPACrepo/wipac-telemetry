"""Tools for working with spans."""


import asyncio
import inspect
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, List, Optional

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


class SpanBehavior(Enum):
    """Enum for indicating type of span behavior is wanted."""

    CURRENT_END_ON_EXIT = auto()
    CURRENT_LEAVE_OPEN_ON_EXIT = auto()
    INDEPENDENT_SPAN = auto()


class InvalidSpanBehaviorValue(ValueError):
    """Raise when an invalid SpanBehvior value is attempted."""


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
    # TODO - what is `is_remote`?
    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Span:
            span_name = name if name else func.__qualname__  # Ex: MyClass.method
            tracer_name = inspect.getfile(func)  # Ex: /path/to/source_file.py

            if behavior == SpanBehavior.INDEPENDENT_SPAN and links and "span" in links:
                raise ValueError(
                    "Cannot self-link the independent/injected span: `span`"
                )

            func_inspect = FunctionInspector(func, args, kwargs)

            if kind == SpanKind.SERVER:
                context = extract(func_inspect.resolve_attr("self.request.headers"))
            else:
                context = None  # `None` will default to current context

            _attrs = func_inspect.wrangle_span_attributes(all_args, these, attributes)
            _links = func_inspect.get_links(links)

            tracer = trace.get_tracer(tracer_name)
            span = tracer.start_span(
                span_name, context=context, kind=kind, attributes=_attrs, links=_links
            )

            LOGGER.info(
                f"Started span `{span_name}` for tracer `{tracer_name}` with: "
                f"attributes={list(_attrs.keys()) if _attrs else []}, "
                f"links={[k.context for k in _links]}"
            )

            return span

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Function")
            span = setup(args, kwargs)

            if behavior.INDEPENDENT_SPAN:
                kwargs["span"] = span
                return func(*args, **kwargs)
            elif SpanBehavior.CURRENT_END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    return func(*args, **kwargs)
            elif SpanBehavior.CURRENT_LEAVE_OPEN_ON_EXIT:
                with trace.use_span(span, end_on_exit=False):
                    return func(*args, **kwargs)
            else:
                raise InvalidSpanBehaviorValue(behavior)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Generator Function")
            span = setup(args, kwargs)

            # TODO

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Async Function")
            span = setup(args, kwargs)

            # TODO

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            if inspect.isgeneratorfunction(func):
                return gen_wrapper
            else:
                return wrapper

    return inner_function


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
    # TODO - what is `is_remote`?
    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Span:
            func_inspect = FunctionInspector(func, args, kwargs)
            span = func_inspect.get_span(span_var_name)

            _attrs = func_inspect.wrangle_span_attributes(all_args, these, attributes)
            if _attrs:
                for key, value in _attrs.items():
                    span.set_attribute(key, value)  # TODO - check for duplicates

            LOGGER.info(
                f"Re-using span `{span.name}` (from '{span_var_name}') with: "
                f"additional attributes={list(_attrs.keys()) if _attrs else []}"
            )

            return span

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Re-Spanned Function")
            span = setup(args, kwargs)

            if behavior.INDEPENDENT_SPAN:
                kwargs["span"] = span
                return func(*args, **kwargs)
            elif SpanBehavior.CURRENT_END_ON_EXIT:
                with trace.use_span(span, end_on_exit=True):
                    return func(*args, **kwargs)
            elif SpanBehavior.CURRENT_LEAVE_OPEN_ON_EXIT:
                with trace.use_span(span, end_on_exit=False):
                    return func(*args, **kwargs)
            else:
                raise InvalidSpanBehaviorValue(behavior)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Re-Spanned Generator Function")
            span = setup(args, kwargs)

            # TODO

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Re-Spanned Async Function")
            span = setup(args, kwargs)

            # TODO

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            if inspect.isgeneratorfunction(func):
                return gen_wrapper
            else:
                return wrapper

    return inner_function


def make_link(
    span: Span, purpose: str, other_attributes: types.Attributes = None
) -> Link:
    """Make a Link for a Span (context) with a collection of attributes."""
    attrs = dict(other_attributes) if other_attributes else {}
    attrs["purpose"] = purpose

    return Link(span.get_span_context(), attributes=convert_to_attributes(attrs))
