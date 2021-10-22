"""Init."""


import os
import sys

# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import]
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import]
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
from opentelemetry.sdk.trace.export import (  # type: ignore[import]
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import (  # noqa
    Link,
    Span,
    SpanKind,
    get_current_span,
    get_tracer_provider,
    set_tracer_provider,
)

from .config import CONFIG
from .events import add_event, evented  # noqa
from .propagations import (  # noqa
    extract_links_carrier,
    inject_links_carrier,
    inject_span_carrier,
    span_to_link,
)
from .spans import CarrierRelation, SpanBehavior, respanned, spanned  # noqa

__all__ = [
    "add_event",
    "CarrierRelation",
    "evented",
    "extract_links_carrier",
    "get_current_span",
    "inject_links_carrier",
    "inject_span_carrier",
    "Link",
    "respanned",
    "Span",
    "span_to_link",
    "SpanBehavior",
    "SpanKind",
    "spanned",
]


# Config SDK ###########################################################################

main_mod_abspath = os.path.abspath(sys.modules["__main__"].__file__)
if main_mod_abspath.endswith("/__main__.py"):
    # this means client is running as a module, so use the directory's name
    common_name = main_mod_abspath.split("/")[-2]  # ex: 'mymodule'
    # keep the parent path for reference
    reference_name = main_mod_abspath.rstrip(f"/{common_name}/__main__.py")
else:
    # otherwise, client is running as a script, so use the file's name
    common_name = main_mod_abspath.split("/")[-1]  # ex: 'myscript.py'
    # keep the parent path for reference
    reference_name = main_mod_abspath.rstrip(f"/{common_name}")

set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: f"{common_name} ({reference_name})"})
    )
)


if CONFIG["WIPACTEL_EXPORT_STDOUT"]:
    get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # output to stdout
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

if CONFIG["OTEL_EXPORTER_OTLP_ENDPOINT"]:
    get_tracer_provider().add_span_processor(  # type: ignore[attr-defined]
        # relies on env variables
        # -- https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html
        # OTEL_EXPORTER_OTLP_TRACES_TIMEOUT
        # OTEL_EXPORTER_OTLP_TRACES_PROTOCOL
        # OTEL_EXPORTER_OTLP_TRACES_HEADERS
        # OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
        # OTEL_EXPORTER_OTLP_TRACES_COMPRESSION
        # OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE
        # OTEL_EXPORTER_OTLP_TIMEOUT
        # OTEL_EXPORTER_OTLP_PROTOCOL
        # OTEL_EXPORTER_OTLP_HEADERS
        # OTEL_EXPORTER_OTLP_ENDPOINT
        # OTEL_EXPORTER_OTLP_COMPRESSION
        # OTEL_EXPORTER_OTLP_CERTIFICATE
        BatchSpanProcessor(OTLPSpanExporter())
    )
