"""Init."""


import os
from distutils.util import strtobool

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import]
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
from opentelemetry.sdk.trace.export import (  # type: ignore[import]
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from . import propagations  # noqa
from .events import evented  # noqa
from .spans import make_link, spanned  # noqa
from .utils import Link, OptSpan, Span, SpanKind, get_current_span  # noqa

__all__ = [
    "propagations",
    "evented",
    "make_link",
    "spanned",
    "Link",
    "OptSpan",
    "Span",
    "SpanKind",
    "get_current_span",
]

# Config SDK ###########################################################################

trace.set_tracer_provider(TracerProvider())

trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
    # output to stdout
    SimpleSpanProcessor(ConsoleSpanExporter())
)

if strtobool(os.environ.get("WIPACTEL_EXPORT_OTLP", "0").lower()):
    trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # relies on env variables
        # -- https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html
        BatchSpanProcessor(OTLPSpanExporter())
    )
