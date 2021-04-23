"""Example script for the evented() decorator."""

import logging
import os
import sys

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing  # noqa: E402 # pylint: disable=C0413,E0401


@tracing.tools.evented(attributes={"city": "Liverpool"})
def evented_outer_function(beatle: str) -> None:
    """Print from this evented outer function."""
    print(beatle)


class EventExampleClass:
    """An example class for events."""

    @tracing.tools.evented()
    def evented_fellow_method(self, beatle: str) -> None:
        """Print from this evented instance method."""
        print(beatle)

    @staticmethod
    @tracing.tools.evented()
    def evented_fellow_static_method(beatle: str) -> None:
        """Print from this evented static method."""
        print(beatle)

    @tracing.tools.spanned()
    @tracing.tools.evented(attributes={"what": "an event!"})
    def spanned_and_evented_fellow_method(self, beatle: str) -> None:
        """Print from this spanned & evented instance method."""
        print(beatle)

    @tracing.tools.evented()
    @tracing.tools.spanned()
    def evented_and_spanned_fellow_method(self, beatle: str) -> None:
        """Print from this evented & spanned instance method."""
        print(beatle)

    @tracing.tools.spanned(use_args=True)
    def spanned_caller_method(self, album: str, year: int) -> None:
        """Call evented methods/functions in this method."""
        print(album)
        print(year)

        self.evented_fellow_method("John")
        EventExampleClass.evented_fellow_static_method("Paul")
        evented_outer_function("George")

        @tracing.tools.evented(these_args=["beatle", "drums"])
        def evented_local_function(beatle: str, song: str, drums: bool = False) -> None:
            print(beatle)
            print(song)
            print(drums)

        evented_local_function("Ringo", "Octopus's Garden", drums=True)

        self.spanned_and_evented_fellow_method("The Fifth Beatle...")
        self.evented_and_spanned_fellow_method("The Sixth Beatle?!")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE CLASS METHOD #1")
    EventExampleClass().spanned_caller_method(
        "Sgt. Pepper's Lonely Hearts Club Band", 1967
    )
