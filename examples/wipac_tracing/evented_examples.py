"""Example script for the evented() decorator."""

import logging
import os
import sys

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing  # noqa: E402 # pylint: disable=C0413,E0401

########################################################################################


@tracing.tools.evented(attributes={"city": "Liverpool"})
def evented_outer_function(beatle: str) -> None:
    """Print from this evented outer function."""
    logging.info("evented_outer_function()")
    print(beatle)


class _ClassForAttribute:
    def __init__(self) -> None:
        self.msg = "the message"


class EventExampleClass:
    """An example class for events."""

    klass = "Klass"

    def __init__(self) -> None:
        self.selfie = "Kodak"
        self.cfa = _ClassForAttribute()

    @tracing.tools.evented(these=["self.selfie", "self.klass", "self.cfa.msg"])
    def evented_fellow_method(self, beatle: str) -> None:
        """Print from this evented instance method."""
        logging.info("evented_fellow_method()")
        print(beatle)

    @staticmethod
    @tracing.tools.evented(name="static-method-001")
    def evented_fellow_static_method(beatle: str) -> None:
        """Print from this evented static method."""
        logging.info("evented_fellow_static_method()")
        print(beatle)

    @tracing.tools.spanned()
    @tracing.tools.evented(attributes={"what": "an event!"})
    def spanned_and_evented_fellow_method(self, beatle: str) -> None:
        """Print from this spanned & evented instance method."""
        logging.info("spanned_and_evented_fellow_method()")
        print(beatle)

    @tracing.tools.evented()
    @tracing.tools.spanned()
    def evented_and_spanned_fellow_method(self, beatle: str) -> None:
        """Print from this evented & spanned instance method."""
        logging.info("evented_and_spanned_fellow_method()")
        print(beatle)

    @tracing.tools.spanned(all_args=True, these=["self.selfie"])
    def spanned_caller_method(self, album: str, year: int) -> None:
        """Call evented methods/functions in this method."""
        logging.info("spanned_caller_method()")
        print(album)
        print(year)

        self.evented_fellow_method("John")
        EventExampleClass.evented_fellow_static_method("Paul")
        evented_outer_function("George")

        @tracing.tools.evented(these=["beatle", "drums"], attributes={"year": year})
        def evented_local_function(beatle: str, song: str, drums: bool = False) -> None:
            logging.info("evented_local_function()")
            print(beatle)
            print(song)
            print(drums)

        evented_local_function("Ringo", "Octopus's Garden", drums=True)

        self.spanned_and_evented_fellow_method("The Fifth Beatle...")
        self.evented_and_spanned_fellow_method("The Sixth Beatle?!")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1 - CLASS METHOD")
    EventExampleClass().spanned_caller_method(
        "Sgt. Pepper's Lonely Hearts Club Band", 1967
    )
