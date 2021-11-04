"""Init."""

import datetime
import hashlib
import importlib
import os
import sys
from pathlib import Path

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


def _pseudo_log(msg: str) -> None:
    print(f"[wipac-telemetry-setup] {msg}", file=sys.stderr)


def _get_version(package: str) -> str:
    """Get the version from the module; if that fails, grab today's date."""
    try:
        mod = importlib.import_module(package.split(".")[0])  # use base package name
        triple = mod.version_info[:3]  # type: ignore[attr-defined]  # ex: (1,2,3)
        version = "v" + ".".join(f"{x:02d}" for x in triple)  # ex: v01.02.03
    except:  # noqa: E722 # pylint:disable=bare-except
        version = datetime.date.today().isoformat()

    return version


def get_service_name() -> str:
    """Build the service name from module/script auto-detection."""
    main_mod = sys.modules["__main__"]
    package = getattr(main_mod, "__package__", False)

    if package:
        # this means client is running as a module, so get the full package name + version
        _pseudo_log(f"Detecting Service Name from `{package}`...")
        version = _get_version(package)
        service_name = f"{package} ({version})"
    else:
        # otherwise, client is running as a script, so use the file's name
        try:
            main_mod_abspath = Path(os.path.abspath(main_mod.__file__))
        except AttributeError as e:
            raise RuntimeError(
                "WIPAC Telemetry service started up before '__main__' was set. "
                "Do you have imports in your package's base '__init__.py'? "
                "If so, remove them; one of these likely prematurely called "
                "this library before '__main__.py' was executed."
            ) from e

        _pseudo_log(f"Detecting Service Name from `{main_mod_abspath}`...")
        script = main_mod_abspath.name  # ex: 'myscript.py'
        with open(main_mod_abspath, "rb") as f:
            readable_hash = hashlib.sha256(f.read()).hexdigest()
        service_name = f"./{script} ({readable_hash[-4:]})"

    # check if user supplied a prefix
    if CONFIG["WIPACTEL_SERVICE_NAME_PREFIX"]:
        _pseudo_log(f"with prefix: \"{CONFIG['WIPACTEL_SERVICE_NAME_PREFIX']}\"")
        service_name = f"{CONFIG['WIPACTEL_SERVICE_NAME_PREFIX']}/{service_name}"

    _pseudo_log(f'Using Service Name: "{service_name}"')
    return service_name


if CONFIG["WIPACTEL_EXPORT_STDOUT"] or CONFIG["OTEL_EXPORTER_OTLP_ENDPOINT"]:
    _pseudo_log("Setting Tracer Provider...")
    set_tracer_provider(
        TracerProvider(resource=Resource.create({SERVICE_NAME: get_service_name()}))
    )
else:
    # tracing is "turned-off" but we still need a Tracer Provider b/c the decorators still fire
    set_tracer_provider(TracerProvider())

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

if CONFIG["WIPACTEL_EXPORT_STDOUT"] or CONFIG["OTEL_EXPORTER_OTLP_ENDPOINT"]:
    _pseudo_log("Setup complete.")
