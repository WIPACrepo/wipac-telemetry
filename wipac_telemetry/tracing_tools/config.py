"""Tracing config file."""

import logging
from typing import TypedDict, cast

from wipac_dev_tools import from_environment
from wipac_dev_tools.enviro_tools import KeySpec


class _TypedConfig(TypedDict):
    OTEL_EXPORTER_OTLP_ENDPOINT: str
    WIPACTEL_EXPORT_STDOUT: bool
    WIPACTEL_LOGGING_LEVEL: str


defaults: _TypedConfig = {
    "OTEL_EXPORTER_OTLP_ENDPOINT": "",
    "WIPACTEL_EXPORT_STDOUT": True,
    "WIPACTEL_LOGGING_LEVEL": "WARNING",
}
CONFIG = cast(_TypedConfig, from_environment(cast(KeySpec, defaults)))


LOGGER = logging.getLogger("wipac-telemetry")
LOGGER.setLevel(CONFIG["WIPACTEL_LOGGING_LEVEL"])
