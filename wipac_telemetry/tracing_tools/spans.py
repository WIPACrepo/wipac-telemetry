"""Tools for working with spans."""


import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple, Union

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.util import types

from .utils import (
    LOGGER,
    Args,
    FunctionInspection,
    Kwargs,
    Link,
    Span,
    SpanKind,
    convert_to_attributes,
    wrangle_attributes,
)


def spanned(
    name: Optional[str] = None,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
    inject: bool = False,
    links: Optional[List[str]] = None,
    kind: Union[SpanKind, str] = SpanKind.INTERNAL,
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Wraps a `tracer.start_as_current_span()` context.

    Keyword Arguments:
        name -- name of span; if not provided, use function's qualified name
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        inject -- whether to inject the span instance into the function (as `span`).
                  (`inject=True` won't set as current span nor automatically exit once function is done.)
        links -- a list of variable names of `Link` instances (span-links) - useful for cross-process tracing
        kind -- either a `SpanKind` enum value or an equivalent str
                - `"INTERNAL"`/`SpanKind.INTERNAL` - (default) normal, in-application spans
                - `"CLIENT"`/`SpanKind.CLIENT` - spanned function makes outgoing cross-service requests
                - `"SERVER"`/`SpanKind.SERVER` - spanned function handles incoming cross-service requests
                    * contextually connected to a client-service's span via parent pointer
                    * (looks at `self.request` instance for necessary info)
                - `"CONSUMER"`/`SpanKind.CONSUMER` - spanned function makes outgoing cross-service messages
                - `"PRODUCER"`/`SpanKind.PRODUCER` - spanned function handles incoming cross-service messages

    Raises a `ValueError` when attempting to self-link the injected span.
    """
    # TODO - what is `is_remote`?
    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Tuple[trace.Tracer, str, Kwargs]:
            span_name = name if name else func.__qualname__  # Ex: MyClass.method
            tracer_name = inspect.getfile(func)  # Ex: /path/to/source_file.py

            if inject and links and "span" in links:
                raise ValueError("Cannot self-link the injected span: `span`")

            func_inspect = FunctionInspection(func, args, kwargs)

            if isinstance(kind, SpanKind):
                _kind = kind
            else:
                _kind = SpanKind[kind.lower()]  # type: ignore[misc]

            if _kind == SpanKind.SERVER:
                context = extract(func_inspect.rget("self.request.headers"))
            else:
                context = None  # `None` will default to current context

            _attrs = wrangle_attributes(attributes, func_inspect, all_args, these)
            _links = _wrangle_links(func_inspect, links)

            tracer = trace.get_tracer(tracer_name)

            LOGGER.info(
                f"Started span `{span_name}` for tracer `{tracer_name}` with: "
                f"attributes={list(_attrs.keys()) if _attrs else []}, "
                f"links={[k.context for k in _links]}"
            )

            return (
                tracer,
                span_name,
                {
                    "context": context,
                    "kind": _kind,
                    "attributes": _attrs,
                    "links": _links,
                },
            )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Function")
            tracer, span_name, setup_kwargs = setup(args, kwargs)

            if inject:
                kwargs["span"] = tracer.start_span(span_name, **setup_kwargs)
                return func(*args, **kwargs)
            else:
                with tracer.start_as_current_span(span_name, **setup_kwargs):
                    return func(*args, **kwargs)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Generator Function")
            tracer, span_name, setup_kwargs = setup(args, kwargs)

            if inject:
                kwargs["span"] = tracer.start_span(span_name, **setup_kwargs)
                for val in func(*args, **kwargs):
                    yield val
            else:
                with tracer.start_as_current_span(span_name, **setup_kwargs):
                    for val in func(*args, **kwargs):
                        yield val

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Async Function")
            tracer, span_name, setup_kwargs = setup(args, kwargs)

            if inject:
                kwargs["span"] = tracer.start_span(span_name, **setup_kwargs)
                return await func(*args, **kwargs)
            else:
                with tracer.start_as_current_span(span_name, **setup_kwargs):
                    return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            if inspect.isgeneratorfunction(func):
                return gen_wrapper
            else:
                return wrapper

    return inner_function


def _wrangle_links(
    func_inspect: FunctionInspection, links: Optional[List[str]],
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


def make_link(
    span: Span, purpose: str, other_attributes: types.Attributes = None
) -> Link:
    """Make a Link for a Span (context) with a collection of attributes."""
    attrs = dict(other_attributes) if other_attributes else {}
    attrs["purpose"] = purpose

    return Link(span.get_span_context(), attributes=convert_to_attributes(attrs))
