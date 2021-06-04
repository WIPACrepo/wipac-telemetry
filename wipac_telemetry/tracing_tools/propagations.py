"""Tools for cross-service propagation."""


import pickle
from typing import Any, Dict, Optional, cast

from opentelemetry import propagate
from opentelemetry.trace import Link, get_current_span
from opentelemetry.util import types

from .utils import convert_to_attributes

_LINK_KEY = "WIPAC-TEL-LINK"


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


def inject_link_carrier(
    carrier: Optional[Dict[str, Any]] = None, attrs: types.Attributes = None
) -> Dict[str, Any]:
    """Add current span info to a dict ("carrier") for distributed tracing.

    Adds a key, `_LINK_KEY`, which can be used by the receiving span to
    make a lateral/link connection (`link`). This is a necessary step for
    distributed tracing between threads, processes, services, etc.

    Optionally, pass in a ready-to-ship dict. This is for situations
    where the carrier needs to be a payload within an established
    protocol, like a headers dict.

    Keyword Arguments:
        carrier -- *see above*
        attrs -- a collection of attributes that further describe the link connection

    Returns the carrier (dict) with the added info.
    """
    if not carrier:
        carrier = {}

    link = Link(get_current_span().get_span_context(), convert_to_attributes(attrs))
    carrier[_LINK_KEY] = pickle.dumps(link)

    return carrier


def extract_link_carrier(carrier: Dict[str, Any]) -> Optional[Link]:
    """Extract the serialized `Link` instance from the carrier.

    If there is no link, then return None. Does not type-check.
    """
    try:
        return cast(Link, pickle.loads(carrier[_LINK_KEY]))
    except KeyError:
        return None
