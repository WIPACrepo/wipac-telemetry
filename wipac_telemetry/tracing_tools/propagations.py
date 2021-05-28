"""Tools for cross-service propagation."""


from typing import Any, Dict, Optional

from opentelemetry import propagate  # type: ignore[import]


def inject_span_carrier(carrier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Inject current tracing info into a dict for inter-context spanning.

    This is a necessary step to make a span parent-child connection
    between threads, processes, services, etc.

    Optionally, pass in a ready-to-ship dict. This is for situations
    where the carrier needs to be serializable, like the HTTP headers
    dict.
    """
    if not carrier:
        carrier = {}

    propagate.inject(carrier)

    return carrier
