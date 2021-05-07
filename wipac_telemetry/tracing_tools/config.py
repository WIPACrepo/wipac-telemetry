"""Tracing config file."""

import logging
import os
from distutils.util import strtobool

CONFIG = dict(os.environ)
CONFIG.update(
    {
        "WIPACTEL_EXPORT_STDOUT": strtobool(
            CONFIG.get("WIPACTEL_EXPORT_STDOUT", "YES").lower()
        ),
        "WIPACTEL_EXPORT_OTLP": strtobool(
            CONFIG.get("WIPACTEL_EXPORT_OTLP", "NO").lower()
        ),
        "WIPACTEL_LOGGING_LEVEL": CONFIG.get(
            "WIPACTEL_LOGGING_LEVEL", "WARNING"
        ).upper(),
    }
)


LOGGER = logging.getLogger("wipac-telemetry")
