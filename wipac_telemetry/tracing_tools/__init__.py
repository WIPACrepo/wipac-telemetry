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


def _pseudo_log(msg: str) -> None:
    print(f"[wipac-telemetry-setup] {msg}", file=sys.stderr)


def get_service_name() -> str:
    """Build the service name from module/script auto-detection."""
    try:
        main_mod_abspath = os.path.abspath(sys.modules["__main__"].__file__)
    except AttributeError as e:
        raise RuntimeError(
            "WIPAC Telemetry service started up before '__main__' was set. "
            "Do you have imports in your package's base '__init__.py'? "
            "If so, remove them; one of these likely prematurely called "
            "this library before '__main__.py' was executed."
        ) from e
    _pseudo_log(f"Detecting Service Name from `{main_mod_abspath}`...")

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

    # check if user supplied a prefix
    if CONFIG["WIPACTEL_SERVICE_NAME_PREFIX"]:
        _pseudo_log(f"with prefix: \"{CONFIG['WIPACTEL_SERVICE_NAME_PREFIX']}\"")
        service_name = f"{CONFIG['WIPACTEL_SERVICE_NAME_PREFIX']}/{service_name}"

    _pseudo_log(f'Using Service Name: "{service_name}"')
    return service_name


_pseudo_log("Setting Tracer Provider...")
set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: get_service_name()}))
)


if CONFIG["WIPACTEL_EXPORT_STDOUT"]:
    _pseudo_log("Adding ConsoleSpanExporter")
    get_tracer_provider().add_span_processor(
        # output to stdout
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

if CONFIG["OTEL_EXPORTER_OTLP_ENDPOINT"]:
    _pseudo_log(f"Adding OTLPSpanExporter ({CONFIG['OTEL_EXPORTER_OTLP_ENDPOINT']})")
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

_pseudo_log("Setup complete.")
