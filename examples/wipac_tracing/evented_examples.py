"""Example script for the evented() decorator."""

import asyncio
import logging
import os
import sys
import time
from typing import Generator

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing_tools  # noqa: E402 # pylint: disable=C0413,E0401

########################################################################################


@tracing_tools.evented(attributes={"city": "Liverpool"})
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

    @tracing_tools.evented(these=["self.selfie", "self.klass", "self.cfa.msg"])
    def evented_fellow_method(self, beatle: str) -> None:
        """Print from this evented instance method."""
        logging.info("evented_fellow_method()")
        print(beatle)

    @staticmethod
    @tracing_tools.evented(name="static-method-001")
    def evented_fellow_static_method(beatle: str) -> None:
        """Print from this evented static method."""
        logging.info("evented_fellow_static_method()")
        print(beatle)

    @tracing_tools.spanned()
    @tracing_tools.evented(attributes={"what": "an event!"})
    def spanned_and_evented_fellow_method(self, beatle: str) -> None:
        """Print from this spanned & evented instance method."""
        logging.info("spanned_and_evented_fellow_method()")
        print(beatle)

    @tracing_tools.evented()
    @tracing_tools.spanned()
    def evented_and_spanned_fellow_method(self, beatle: str) -> None:
        """Print from this evented & spanned instance method."""
        logging.info("evented_and_spanned_fellow_method()")
        print(beatle)

    @tracing_tools.spanned(all_args=True, these=["self.selfie"])
    def spanned_caller_method(self, album: str, year: int) -> None:
        """Call evented methods/functions in this method."""
        logging.info("spanned_caller_method()")
        print(album)
        print(year)

        self.evented_fellow_method("John")
        EventExampleClass.evented_fellow_static_method("Paul")
        evented_outer_function("George")

        @tracing_tools.evented(these=["beatle", "drums"], attributes={"year": year})
        def evented_local_function(beatle: str, song: str, drums: bool = False) -> None:
            logging.info("evented_local_function()")
            print(beatle)
            print(song)
            print(drums)

        evented_local_function("Ringo", "Octopus's Garden", drums=True)

        self.spanned_and_evented_fellow_method("The Fifth Beatle...")
        self.evented_and_spanned_fellow_method("The Sixth Beatle?!")


@tracing_tools.spanned()
async def example_2_async() -> None:
    """Print and log simple message."""

    @tracing_tools.evented()
    def _inner_sync() -> None:
        print("inner-sync function")

    @tracing_tools.evented()
    async def _inner_async() -> None:
        await asyncio.sleep(2)
        print("inner-async function")

    _inner_sync()
    await _inner_async()
    print("Done with async example.")


@tracing_tools.spanned()
def example_3_iter_a_generator() -> None:
    """Span a generator."""

    @tracing_tools.evented()
    def _gen() -> Generator[int, None, None]:
        for i in range(5):
            yield i

    gen = _gen()
    time.sleep(1)
    for num in gen:
        print(num)
        time.sleep(0.25)

    for num in _gen():
        print(num)
        time.sleep(0.25)


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1 - CLASS METHOD")
    EventExampleClass().spanned_caller_method(
        "Sgt. Pepper's Lonely Hearts Club Band", 1967
    )

    logging.warning("EXAMPLE #2 - NESTED ASYNC")
    asyncio.get_event_loop().run_until_complete(example_2_async())

    logging.warning("EXAMPLE #3 - GENERATOR")
    example_3_iter_a_generator()
