"""Tools for cross-service propagation."""


import pickle
from typing import Any, Dict, List, Optional

from opentelemetry import propagate
from opentelemetry.trace import Link, Span, get_current_span
from opentelemetry.util import types

from .config import LOGGER
from .utils import convert_to_attributes

_LINKS_KEY = "WIPAC-TEL-LINKS"


class _LinkSerialization:
    @staticmethod
    def encode_links(links: List[Link]) -> bytes:
        """Custom encoding for sending links."""
        deconstructed = []
        for link in links:
            attrs = dict(link.attributes) if link.attributes else {}
            LOGGER.debug(f"Encoding Link: {link.context} w/ {attrs}")
            deconstructed.append((link.context, attrs))

        return pickle.dumps(deconstructed)

    @staticmethod
    def decode_links(obj: Any) -> List[Link]:
        """Counterpart decoding for receiving links."""
        links = []
        for span_context, attrs in pickle.loads(obj):
            LOGGER.debug(f"Decoding Link: {span_context} w/ {attrs}")
            links.append(Link(span_context, convert_to_attributes(attrs)))

        return links


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

    LOGGER.info(f"Injecting Span Carrier: {carrier}")
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

    LOGGER.info(f"Injecting Links Carrier: {carrier}")
    links = [Link(get_current_span().get_span_context(), convert_to_attributes(attrs))]
    if addl_links:
        links.extend(addl_links)

    carrier[_LINKS_KEY] = _LinkSerialization.encode_links(links)

    return carrier


def extract_links_carrier(carrier: Dict[str, Any]) -> List[Link]:
    """Extract the serialized `Link` instances from the carrier.

    If there is no link, then return empty list. Does not type-check.
    """
    LOGGER.info(f"Extracting Links Carrier: {carrier}")
    try:
        return _LinkSerialization.decode_links(carrier[_LINKS_KEY])
    except KeyError:
        return []


def span_to_link(span: Span, attrs: types.Attributes = None) -> Link:
    """Create a link using a span instance and a collection of attributes."""
    return Link(span.get_span_context(), convert_to_attributes(attrs))
