"""Init."""

import datetime
import hashlib
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
from wipac_dev_tools import SetupShop

from .config import CONFIG, LOGGER
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

print(LOGGER)


def get_service_name() -> str:
    """Build the service name from module/script auto-detection."""
    main_mod_abspath = os.path.abspath(sys.modules["__main__"].__file__)
    print(
        f"DEBUG: Detecting Service Name from `{main_mod_abspath}`...", file=sys.stderr
    )

    if main_mod_abspath.endswith("/__main__.py"):
        # this means client is running as a module, so get the full package name + version
        name = main_mod_abspath.rstrip("__main__.py").split("/")[-1]
        here = main_mod_abspath.rstrip(f"/{name}/__main__.py")
        try:
            # pylint:disable=protected-access
            version = SetupShop._get_version(here, name)
            version = ".".join([x.zfill(2) for x in version.split(".")])  # ex: 01.02.03
            version = "v" + version
        except:  # noqa: E722 # pylint:disable=bare-except
            version = datetime.date.today().isoformat()
        service_name = f"{sys.modules['__main__'].__package__} ({version})"
    else:
        # otherwise, client is running as a script, so use the file's name
        script = main_mod_abspath.split("/")[-1]  # ex: 'myscript.py'
        with open(main_mod_abspath, "rb") as f:
            readable_hash = hashlib.sha256(f.read()).hexdigest()
        service_name = f"./{script} ({readable_hash[-4:]})"

    print(f"DEBUG: Using Service Name: {service_name}...", file=sys.stderr)
    return service_name


print("INFO: Setting Tracer Provider...", file=sys.stderr)
set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: get_service_name()}))
)


if CONFIG["WIPACTEL_EXPORT_STDOUT"]:
    print("INFO: Adding ConsoleSpanExporter...", file=sys.stderr)
    get_tracer_provider().add_span_processor(
        # output to stdout
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

if CONFIG["OTEL_EXPORTER_OTLP_ENDPOINT"]:
    print(
        "INFO: Adding OTLPSpanExporter ({CONFIG['OTEL_EXPORTER_OTLP_ENDPOINT']})...",
        file=sys.stderr,
    )
    get_tracer_provider().add_span_processor(
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
