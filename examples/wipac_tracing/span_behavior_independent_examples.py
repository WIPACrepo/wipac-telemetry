"""Example script for the spanned() decorator utilizing span-injection."""

import logging
import os
import random
import sys

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing_tools  # noqa: E402 # pylint: disable=C0413,E0401

########################################################################################


class DemoPitfallsClass:
    """Handle methods using a Span instance as a instance variable."""

    def __init__(self) -> None:
        self.method_that_also_starts_a_span()
        self.span.add_event("(__init__) started span from instance method")

    @tracing_tools.spanned(behavior=tracing_tools.SpanBehavior.INDEPENDENT_SPAN)
    def method_that_also_starts_a_span(
        self, span: tracing_tools.OptSpan = None
    ) -> None:
        """Do some things and start an independent span."""
        assert span
        assert span.is_recording()
        assert not tracing_tools.get_current_span().is_recording()
        self.span = span
        self.span.add_event("(method) started span from instance method")

    ##################

    # NOT OKAY - just avoid __del__ + Span.end(), interaction seems undefined
    # def __del__(self) -> None:
    #     """ERROR: ending an instance-dependent span in __del__ is not supported, will break."""
    #     if self.span:
    #         self.span.add_event("__del__")
    #         self.span.end()

    # USE THIS INSTEAD
    def end(self) -> None:
        """Clean up."""
        if self.span:
            self.span.add_event("manually ending span")
            self.span.end()


########################################################################################


class ExternalClass:
    """Handle methods using a Span instance as a instance variable."""

    def __init__(self, span: tracing_tools.Span) -> None:
        self.span = span

    @tracing_tools.spanned()  # sets current_span
    def disjoint_spanned_method(self):
        """A method containing an distinct/unrelated span context."""
        print("disjoint_spanned_method")

        @tracing_tools.evented(all_args=True)
        def inner_event(name: str, height: int) -> None:
            print(name)
            print(height)

        inner_event("Hank", 185)

    # NOT OKAY - just avoid __del__ + Span.end(), interaction seems undefined
    # def __del__(self) -> None:
    #     """Clean up."""
    #     if self.span:
    #         self.span.add_event("__del__")
    #         self.span.end()


@tracing_tools.spanned(
    behavior=tracing_tools.SpanBehavior.INDEPENDENT_SPAN, attributes={"a": 1}
)
def injected_span_pass_to_instance(span: tracing_tools.OptSpan = None) -> ExternalClass:
    """Inject a span then pass onto an instance."""
    if not span:
        raise Exception("Span injection failed.")

    span.set_attribute("Random Int", random.randint(0, 9))
    instance = ExternalClass(span)
    instance.disjoint_spanned_method()
    return instance


########################################################################################


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #0 - CLASS METHOD W/ SPAN-INJECTION")
    inst = DemoPitfallsClass()
    # inst.method_that_also_starts_a_span()
    inst.end()  # NOTE: traces aren't sent until the span is closed / raises

    logging.warning("EXAMPLE #1 - FUNCTION W/ SPAN-INJECTION")
    inst = injected_span_pass_to_instance()
    inst.span.end()  # NOTE: traces aren't sent until the span is closed / raises
