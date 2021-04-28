"""Example script for the evented() decorator w/ overriding-spans."""

import logging
import os
import sys
from typing import cast

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing  # noqa: E402 # pylint: disable=C0413,E0401
from wipac_telemetry.tracing.tools import (  # noqa: E402 # pylint: disable=C0413
    OptSpan,
    Span,
)

########################################################################################


@tracing.tools.spanned(inject=True)
def the_one_that_returns_a_span(span: OptSpan = None) -> Span:
    """Use Span-injection to set the span."""
    logging.info("the_one_that_returns_a_span()")
    return cast(Span, span)


@tracing.tools.evented(span="this_span")
def the_one_with_an_overriding_span_event(this_span: Span) -> None:
    """Use an overriding-span to event this function."""
    logging.info("the_one_with_an_overriding_span_event()")


@tracing.tools.evented()
def the_one_that_fails() -> None:
    """Erroneously event this function without a current span context."""
    logging.info("the_one_that_fails()")


def example_1() -> None:
    """Demo function-based overriding-span event."""
    span = the_one_that_returns_a_span()
    the_one_with_an_overriding_span_event(span)

    try:
        the_one_that_fails()
    except RuntimeError as e:
        assert str(e) == "There is no currently recording span context."

    span.end()  # NOTE: traces aren't sent until the span is closed / raises


########################################################################################


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1")
    example_1()
