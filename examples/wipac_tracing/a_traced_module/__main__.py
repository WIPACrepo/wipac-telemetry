"""Dummy module for making spans to look at."""


import logging
import os
import sys

import coloredlogs  # type: ignore[import]

from .an_example import a_function

if "examples" not in os.listdir():
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401


# @wtt.spanned()
def main() -> None:
    """Start up application context."""
    a_function()


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")
    logging.warning("This is a module's __main__")

    # Go
    main()
