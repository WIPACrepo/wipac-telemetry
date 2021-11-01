"""Tracing config file."""

import logging
from typing import cast

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from wipac_dev_tools import from_environment
from wipac_dev_tools.enviro_tools import KeySpec


class _TypedConfig(TypedDict):
    OTEL_EXPORTER_OTLP_ENDPOINT: str
    WIPACTEL_EXPORT_STDOUT: bool
    WIPACTEL_LOGGING_LEVEL: str
    WIPACTEL_SERVICE_NAME_PREFIX: str


defaults: _TypedConfig = {
    "OTEL_EXPORTER_OTLP_ENDPOINT": "",
    "WIPACTEL_EXPORT_STDOUT": False,
    "WIPACTEL_LOGGING_LEVEL": "WARNING",
    "WIPACTEL_SERVICE_NAME_PREFIX": "",
}
CONFIG = cast(_TypedConfig, from_environment(cast(KeySpec, defaults)))


LOGGER = logging.getLogger("wipac-telemetry")
LOGGER.setLevel(CONFIG["WIPACTEL_LOGGING_LEVEL"])
