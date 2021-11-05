"""Tools for cross-service propagation."""


import pickle
from typing import Any, Dict, List, Optional

from opentelemetry import propagate
from opentelemetry.trace import Link, Span, get_current_span
from opentelemetry.util import types

from .utils import convert_to_attributes

_LINKS_KEY = "WIPAC-TEL-LINKS"


class _LinkSerialization:
    @staticmethod
    def encode_links(links: List[Link]) -> bytes:
        """Custom encoding for sending links."""
        encoded = []
        for lk in links:
            print(lk)
            attrs = {}
            if lk.attributes:
                for k, v in lk.attributes.items():
                    attrs[k] = v

            pickle.dumps(lk.context)
            pickle.dumps(int(lk.context.trace_id))
            pickle.dumps(int(lk.context.span_id))
            print(lk.attributes)
            pickle.dumps(lk.attributes)

            print(attrs)
            encoded.append((lk.context, attrs))

        return pickle.dumps(encoded)

    @staticmethod
    def decode_links(obj: Any) -> List[Link]:
        """Counterpart decoding for receiving links."""
        tuples = pickle.loads(obj)
        return [
            Link(span_context, convert_to_attributes(attrs))
            for span_context, attrs in tuples
        ]


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

    print(get_current_span().get_span_context())
    print(convert_to_attributes(attrs))
    pickle.dumps(get_current_span().get_span_context())
    print(
        dir(Link(get_current_span().get_span_context(), convert_to_attributes(attrs)))
    )
    # pickle.dumps( # NOTE: THIS FAILS
    #     Link(get_current_span().get_span_context(), convert_to_attributes(attrs))
    # )
    links = [Link(get_current_span().get_span_context(), convert_to_attributes(attrs))]
    print(dir(links[0].context))
    print(type(links[0].context))
    print(links)

    if addl_links:
        links.extend(addl_links)

    carrier[_LINKS_KEY] = _LinkSerialization.encode_links(links)

    return carrier


def extract_links_carrier(carrier: Dict[str, Any]) -> List[Link]:
    """Extract the serialized `Link` instances from the carrier.

    If there is no link, then return empty list. Does not type-check.
    """
    try:
        return _LinkSerialization.decode_links(carrier[_LINKS_KEY])
    except KeyError:
        return []


def span_to_link(span: Span, attrs: types.Attributes = None) -> Link:
    """Create a link using a span instance and a collection of attributes."""
    return Link(span.get_span_context(), convert_to_attributes(attrs))
