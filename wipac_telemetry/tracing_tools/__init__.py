"""Init."""


from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import]
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
from opentelemetry.sdk.trace.export import (  # type: ignore[import]
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import (  # noqa
    Span,
    SpanKind,
    get_current_span,
    get_tracer_provider,
    set_tracer_provider,
)

from .config import CONFIG
from .events import add_event, evented  # noqa
from .propagations import inject_links_carrier, inject_span_carrier  # noqa
from .spans import CarrierRelation, SpanBehavior, respanned, spanned  # noqa

__all__ = [
    "add_event",
    "evented",
    "get_current_span",
    "inject_links_carrier",
    "inject_span_carrier",
    "CarrierRelation",
    "respanned",
    "Span",
    "SpanBehavior",
    "SpanKind",
    "spanned",
]

# Config SDK ###########################################################################

set_tracer_provider(TracerProvider())

if CONFIG["WIPACTEL_EXPORT_STDOUT"]:
    get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # output to stdout
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

if CONFIG["WIPACTEL_EXPORT_OTLP"]:
    get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # relies on env variables
        # -- https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html
        BatchSpanProcessor(OTLPSpanExporter())
    )
