"""Init."""


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
from .config import CONFIG
from .events import evented  # noqa
from .spans import SpanBehavior, make_link, respanned, spanned  # noqa
from .utils import Link, Span, SpanKind, get_current_span  # noqa

__all__ = [
    "propagations",
    "evented",
    "make_link",
    "spanned",
    "respanned",
    "Link",
    "Span",
    "SpanKind",
    "get_current_span",
    "SpanBehavior",
]

# Config SDK ###########################################################################

trace.set_tracer_provider(TracerProvider())

if CONFIG["WIPACTEL_EXPORT_STDOUT"]:
    trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # output to stdout
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

if CONFIG["WIPACTEL_EXPORT_OTLP"]:
    trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # relies on env variables
        # -- https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html
        BatchSpanProcessor(OTLPSpanExporter())
    )
