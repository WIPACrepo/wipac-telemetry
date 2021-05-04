"""Tools for working with spans."""


import inspect
from functools import wraps
from typing import Any, Callable, List, Optional

from opentelemetry import trace
from opentelemetry.util import types

from .utils import (
    LOGGER,
    FunctionInspection,
    Link,
    Span,
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

            func_inspect = FunctionInspection(func, args, kwargs)
            _attrs = wrangle_attributes(attributes, func_inspect, all_args, these)
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
