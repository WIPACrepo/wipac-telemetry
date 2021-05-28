"""Tools for cross-service propagation."""


from typing import Any, Dict, Optional

from opentelemetry import propagate  # type: ignore[import]


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
