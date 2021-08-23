"""Setup."""


import os
import subprocess

from setuptools import setup  # type: ignore[import]

subprocess.run(
    "pip install git+https://github.com/WIPACrepo/wipac-dev-tools.git".split(),
    check=True,
)
from wipac_dev_tools import SetupShop  # noqa: E402  # pylint: disable=C0413

shop = SetupShop(
    "wipac_telemetry",
    os.path.abspath(os.path.dirname(__file__)),
    ((3, 6), (3, 8)),
    "WIPAC-Specific OpenTelemetry Tools",
    pinned_packages=[
        "coloredlogs",
        "opentelemetry-api",
        "opentelemetry-exporter-jaeger",
        "opentelemetry-exporter-otlp",
        "opentelemetry-propagator-b3",
        "opentelemetry-sdk",
    ],
)

setup(
    **shop.get_kwargs(subpackages=["tracing_tools"]),
    url="https://github.com/WIPACrepo/wipac-telemetry-prototype",
    package_data={shop.name: ["py.typed"]},
)
