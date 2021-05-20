"""Example script for the evented() decorator w/ overriding-spans."""

import logging
import os
import sys
from typing import cast

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401


@wtt.spanned(behavior=wtt.SpanBehavior.DONT_END)
def the_one_that_returns_a_span() -> wtt.Span:
    """Use wtt.Span-injection to set the span."""
    logging.info("the_one_that_returns_a_span()")
    return wtt.get_current_span()


@wtt.evented(span="this_span")
def the_one_with_an_overriding_span_event(this_span: wtt.Span) -> None:
    """Use an overriding-span to event this function."""
    logging.info("the_one_with_an_overriding_span_event()")


@wtt.evented()
def the_one_with_a_plain_event() -> None:
    """Erroneously event this function without a current span context."""
    logging.info("the_one_with_a_plain_event()")


########################################################################################


def example_1_no_current_span_context() -> None:
    """Demo function-based overriding-span event."""
    logging.info("example_1_no_other_span_context()")

    span = the_one_that_returns_a_span()
    the_one_with_an_overriding_span_event(span)

    try:
        the_one_with_a_plain_event()
        assert 0  # I don't want to start making tests, so this'll do for now
    except RuntimeError as e:
        assert str(e) == "There is no currently recording span context."

    span.end()  # NOTE: traces aren't sent until the span is closed / raises


########################################################################################


@wtt.spanned()
def example_2_with_current_span_context() -> None:
    """Demo function-based overriding-span event."""
    logging.info("example_1_no_other_span_context()")

    span = the_one_that_returns_a_span()
    the_one_with_an_overriding_span_event(span)

    the_one_with_a_plain_event()

    span.end()  # NOTE: traces aren't sent until the span is closed / raises


########################################################################################


class TheOneWithAnInstanceAttributeSpan:
    """A class with a span."""

    def __init__(self, span: wtt.Span) -> None:
        self.span = span
        self.id = 54641234724
        self.calls = 0

    @wtt.evented(span="self.span", these=["self.calls"])
    def yet_another_event(self) -> None:
        """Use a self.*-overriding span."""
        logging.info("yet_another_event()")
        self.calls += 300


@wtt.evented(span="inst.span", these=["inst.id"])
def the_one_with_an_overriding_span_event_nested_in_an_instance(
    inst: TheOneWithAnInstanceAttributeSpan,
) -> None:
    """Use an overriding-span to event this function via an instance."""
    logging.info("the_one_with_an_overriding_span_event_nested_in_an_instance()")
    inst.calls += 150


@wtt.spanned()
def example_3_instance_attribute_overrding_span() -> None:
    """Demo function-based overriding-span event."""
    logging.info("example_3_instance_attribute_overrding_span()")

    span = the_one_that_returns_a_span()
    inst = TheOneWithAnInstanceAttributeSpan(span)
    the_one_with_an_overriding_span_event_nested_in_an_instance(inst)
    inst.yet_another_event()
    span.end()  # NOTE: traces aren't sent until the span is closed / raises


########################################################################################


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1")
    example_1_no_current_span_context()

    logging.warning("EXAMPLE #2")
    example_2_with_current_span_context()

    logging.warning("EXAMPLE #3")
    example_3_instance_attribute_overrding_span()
