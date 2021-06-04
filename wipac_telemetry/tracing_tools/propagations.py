"""Tools for cross-service propagation."""


import pickle
from typing import Any, Dict, List, Optional, cast

from opentelemetry import propagate
from opentelemetry.trace import Link, Span, get_current_span
from opentelemetry.util import types

from .utils import convert_to_attributes

_LINKS_KEY = "WIPAC-TEL-LINKS"


def inject_span_carrier(carrier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Add current span info to a dict ("carrier") for distributed tracing.

    Adds a key, `"traceparent"`, which can be used by the child span to
    make a parent connection (`parent_id`). This is a necessary step for
    distributed tracing between threads, processes, services, etc.

    Optionally, pass in a ready-to-ship dict. This is for situations
    where the carrier needs to be a payload within an established
    protocol, like the HTTP-headers dict.

    Returns the carrier (dict) with the added info.
    """
    if not carrier:
        carrier = {}

    propagate.inject(carrier)

    return carrier


def inject_links_carrier(
    carrier: Optional[Dict[str, Any]] = None,
    attrs: types.Attributes = None,
    addl_links: Optional[List[Link]] = None,
) -> Dict[str, Any]:
    """Add current span info to a dict ("carrier") for distributed tracing.

    Adds a key, `_LINKS_KEY`, which can be used by the receiving span to
    make a lateral/link connection(s) (`links`). This is a necessary step for
    distributed tracing between threads, processes, services, etc.

    Optionally, pass in a ready-to-ship dict. This is for situations
    where the carrier needs to be a payload within an established
    protocol, like a headers dict.

    Keyword Arguments:
        carrier -- *see above*
        attrs -- a collection of attributes that further describe the link connection
                 - uses the current span
        addl_links -- an additional set of links

    Returns the carrier (dict) with the added info.
    """
    if not carrier:
        carrier = {}

    links = [Link(get_current_span().get_span_context(), convert_to_attributes(attrs))]

    if addl_links:
        links.extend(addl_links)

    carrier[_LINKS_KEY] = pickle.dumps(links)

    return carrier


def extract_links_carrier(carrier: Dict[str, Any]) -> List[Link]:
    """Extract the serialized `Link` instances from the carrier.

    If there is no link, then return empty list. Does not type-check.
    """
    try:
        return cast(List[Link], pickle.loads(carrier[_LINKS_KEY]))
    except KeyError:
        return []


def span_to_link(span: Span, attrs: types.Attributes = None) -> Link:
    """Create a link using a span instance and a collection of attributes."""
    return Link(span.get_span_context(), convert_to_attributes(attrs))
