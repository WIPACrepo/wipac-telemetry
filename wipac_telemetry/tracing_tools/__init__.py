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
from .events import evented  # noqa
from .spans import make_link, spanned  # noqa
from .utils import Link, OptSpan, Span, get_current_span  # noqa

# Config SDK ###########################################################################

trace.set_tracer_provider(TracerProvider())

trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
    # output to stdout
    SimpleSpanProcessor(ConsoleSpanExporter())
)
# trace.get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
#     # relies on env variables
#     # -- https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html
#     BatchSpanProcessor(OTLPSpanExporter())
# )
