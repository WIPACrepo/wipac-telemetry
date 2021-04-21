"""Example script for the new_span() decorator."""


import logging
import os
import sys

import coloredlogs  # type: ignore[import]

sys.path.append(".")
from wipac_telemetry import tracing  # noqa: E402 # pylint: disable=C0413,E0401

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")


@tracing.tools.new_span()  # type: ignore[misc]
def example_1_with_no_args() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing.tools.new_span("my-span")  # type: ignore[misc]
def example_2_with_span_name() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing.tools.new_span("my-third-span", "a-new-tracer")  # type: ignore[misc]
def example_3_with_span_and_tracer_name() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing.tools.new_span()  # type: ignore[misc]
def example_4_with_an_uncaught_error() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to raise a FileNotFoundError"
    print(msg)
    logging.info(msg)
    raise FileNotFoundError("My FileNotFoundError message")


@tracing.tools.new_span()  # type: ignore[misc]
def example_5_with_a_caught_error() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to catch my ValueError"
    print(msg)
    logging.info(msg)
    try:
        raise ValueError("My ValueError message")
    except ValueError as e:
        logging.info(f"I caught this: `{e}`")


@tracing.tools.new_span()  # type: ignore[misc]
def example_6_nested_spans() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to call another spanned function w/ the same tracer name/id"
    print(msg)
    logging.info(msg)
    try:
        example_4_with_an_uncaught_error()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1")
    example_1_with_no_args()

    logging.warning("EXAMPLE #2")
    example_2_with_span_name()

    logging.warning("EXAMPLE #3")
    example_3_with_span_and_tracer_name()

    logging.warning("EXAMPLE #4")
    try:
        example_4_with_an_uncaught_error()
    except FileNotFoundError:
        pass

    logging.warning("EXAMPLE #5")
    example_5_with_a_caught_error()

    logging.warning("EXAMPLE #6")
    example_6_nested_spans()
