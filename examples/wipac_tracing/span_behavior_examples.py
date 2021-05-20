"""Example script for the spanned() decorator w/ SpanBehavior values."""

import logging
import os
import random
import sys
import time
from typing import Optional

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401

########################################################################################


class DemoClass:
    """Handle methods using a Span instance as a instance variable."""

    def __init__(self) -> None:
        self.span: Optional[wtt.Span] = None

    @wtt.spanned(behavior=wtt.SpanBehavior.ONLY_END_ON_EXCEPTION)
    def prepare(self) -> None:
        """Do some things and start an independent span."""
        self.span = wtt.get_current_span()
        assert self.span.is_recording()
        self.span.add_event("(method) started span from instance method")
        time.sleep(3)

        @wtt.respanned(None, wtt.SpanBehavior.END_ON_EXIT, all_args=True)
        def legal_but_will_log_warnings(num: int) -> None:
            # this would end the span before the caller does
            pass

        @wtt.respanned(None, wtt.SpanBehavior.ONLY_END_ON_EXCEPTION, all_args=True)
        def legal_and_rare(num: int) -> None:
            # this could end the span, which may or may not be wanted
            pass

        @wtt.respanned(None, wtt.SpanBehavior.DONT_END, all_args=True)
        def legal_and_fine(num: int) -> None:
            # this is okay, and a quick way to add to the span
            pass

        legal_and_rare(11)
        legal_and_fine(22)

    @wtt.respanned(
        "self.span", wtt.SpanBehavior.ONLY_END_ON_EXCEPTION, attributes={"a": 2}
    )
    def process(self) -> None:
        """Do some things and reuse a span."""
        time.sleep(2)
        assert self.span == wtt.get_current_span()
        assert wtt.get_current_span().is_recording()

        # this won't end the span
        try:
            raise KeyError()
        except:  # noqa: E722 # pylint: disable=bare-except
            pass

    @wtt.respanned("self.span", wtt.SpanBehavior.DONT_END)
    def process_with_exception(self) -> None:
        """Do some things and reuse a span."""
        time.sleep(1)
        assert self.span == wtt.get_current_span()
        assert wtt.get_current_span().is_recording()

        # this won't end the span so traces won't be sent,
        # unless the exception is excepted by the caller
        raise Exception("An exception!")

    @wtt.respanned(
        "self.span", wtt.SpanBehavior.END_ON_EXIT, attributes={"b": 3}
    )  # auto-ends
    def finish(self) -> None:
        """Do some things, reuse a span, then close that span."""
        time.sleep(1)
        assert self.span == wtt.get_current_span()
        assert wtt.get_current_span().is_recording()

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

    def __init__(self, span: wtt.Span) -> None:
        self.span = span

    @wtt.spanned()  # sets current_span
    def disjoint_spanned_method(self) -> None:
        """Do some things with a new disjoint span."""
        print("disjoint_spanned_method")
        assert wtt.get_current_span().is_recording()
        assert self.span.is_recording()
        assert self.span != wtt.get_current_span()

        @wtt.evented(all_args=True)
        def inner_event_1(name: str, height: int) -> None:
            print(name)
            print(height)

        @wtt.evented(span="span", all_args=True)
        def inner_event_2(name: str, height: int, span: wtt.Span) -> None:
            assert span.is_recording()
            print(name)
            print(height)

        inner_event_1("Bar", 185)
        inner_event_2("Foo", 177, self.span)

    # NOT OKAY - just avoid __del__ + Span.end(), interaction seems undefined
    # def __del__(self) -> None:
    #     """Clean up."""
    #     if self.span:
    #         self.span.add_event("__del__")
    #         self.span.end()


@wtt.spanned(attributes={"a": 1})  # auto end-on-exit
def injected_span_pass_to_instance() -> ExternalClass:
    """Inject a span then pass onto an instance."""
    assert wtt.get_current_span().is_recording()

    wtt.get_current_span().set_attribute("Random Int", random.randint(0, 9))
    instance = ExternalClass(wtt.get_current_span())
    instance.disjoint_spanned_method()
    return instance


########################################################################################


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1 - CLASS DEMOS")
    inst = DemoClass()
    inst.prepare()
    inst.process()
    try:
        inst.process_with_exception()  # NOTE: this will end the span, excepting it sends traces
    except:  # noqa: E722  # pylint: disable=bare-except
        pass
    inst.finish()  # NOTE: traces aren't sent until the span is closed / raises
    # inst.end()  # NOTE: this is unnecessary -- we'd get a logging warning

    logging.warning("EXAMPLE #2 - FUNCTION DEMOS")
    inst = injected_span_pass_to_instance()
    # inst.span.end()  # NOTE: this is unnecessary -- we'd get a logging warning
