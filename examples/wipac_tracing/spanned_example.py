"""Example script for the spanned() decorator."""


import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing_tools  # noqa: E402 # pylint: disable=C0413,E0401


@tracing_tools.spanned()
def example_1_with_no_args() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


class Example2:
    """An example with an class instance method."""

    @tracing_tools.spanned()
    def example_2_instance_method(self) -> None:
        """Print and log simple message."""
        msg = "Hello World!"
        print(msg)
        logging.info(msg)


@tracing_tools.spanned("my-span")
def example_3_with_name() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing_tools.spanned()
def example_4_with_an_uncaught_error() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to raise a FileNotFoundError"
    print(msg)
    logging.info(msg)
    raise FileNotFoundError("My FileNotFoundError message")


@tracing_tools.spanned()
def example_5_with_a_caught_error() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to catch my ValueError"
    print(msg)
    logging.info(msg)
    try:
        raise ValueError("My ValueError message")
    except ValueError as e:
        logging.info(f"I caught this: `{e}`")


@tracing_tools.spanned()
def example_6_nested_spans() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to call another spanned function w/ the same tracer name/id"
    print(msg)
    logging.info(msg)
    try:
        example_4_with_an_uncaught_error()
    except FileNotFoundError:
        pass


class _MyObject:
    def __init__(self, msg: str) -> None:
        self.msg = msg


@tracing_tools.spanned(all_args=True)
def example_7_attributes_from_sig_vals(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, int]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[List[int]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing_tools.spanned(attributes={"my": 1, "attributes": 2})
def example_8_attributes_only_explicit(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, int]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[List[int]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing_tools.spanned(attributes={"my": 1, "attributes": 2}, all_args=True)
def example_9_attributes_explicit_and_args(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, int]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[List[int]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing_tools.spanned(
    attributes={"my": 1, "attributes": 2}, these=["a0", "a1", "a6", "a0.msg"]
)
def example_10_attributes_explicit_and_whitelisted_args(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, int]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[List[int]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing_tools.spanned()
def example_11_no_attributes(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, int]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[List[int]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@tracing_tools.spanned()
async def example_20_async() -> None:
    """Print and log simple message."""

    @tracing_tools.spanned()
    def example_20_inner_sync() -> None:
        print("inner-sync function")

    @tracing_tools.spanned()
    async def example_20_inner_async() -> None:
        await asyncio.sleep(10)
        print("inner-async function")

    example_20_inner_sync()
    await example_20_inner_async()
    print("Done with async example.")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1")
    example_1_with_no_args()

    logging.warning("EXAMPLE #2")
    Example2().example_2_instance_method()

    logging.warning("EXAMPLE #3")
    example_3_with_name()

    logging.warning("EXAMPLE #4")
    try:
        example_4_with_an_uncaught_error()
    except FileNotFoundError:
        pass

    logging.warning("EXAMPLE #5")
    example_5_with_a_caught_error()

    logging.warning("EXAMPLE #6")
    example_6_nested_spans()

    #
    # Examples with Attributes:

    logging.warning("EXAMPLE #7")
    example_7_attributes_from_sig_vals(
        _MyObject("object won't be an attribute, but `msg`-attribute can be"),
        "arg1",
        "arg2",
        "arg3",
        a4={"dicts": "won't be", "added as": "attributes"},
        a6=["*homogeneous*", "str/bool/int/float", "sequences will be attributes"],
        a7=(1, 2, 3, 4, 5, 6),
        a5=55,
    )

    logging.warning("EXAMPLE #8")
    example_8_attributes_only_explicit(
        _MyObject("object won't be an attribute, but `msg`-attribute can be"),
        "arg1",
        "arg2",
        "arg3",
        a4={"dicts": "won't be", "added as": "attributes"},
        a6=["*homogeneous*", "str/bool/int/float", "sequences will be attributes"],
        a7=(1, 2, 3, 4, 5, 6),
        a5=55,
    )

    logging.warning("EXAMPLE #9")
    example_9_attributes_explicit_and_args(
        _MyObject("object won't be an attribute, but `msg`-attribute can be"),
        "arg1",
        "arg2",
        "arg3",
        a4={"dicts": "won't be", "added as": "attributes"},
        a6=["*homogeneous*", "str/bool/int/float", "sequences will be attributes"],
        a7=(1, 2, 3, 4, 5, 6),
        a5=55,
    )

    logging.warning("EXAMPLE #10")
    example_10_attributes_explicit_and_whitelisted_args(
        _MyObject("object won't be an attribute, but `msg`-attribute can be"),
        "arg1",
        "arg2",
        "arg3",
        a4={"dicts": "won't be", "added as": "attributes"},
        a6=["*homogeneous*", "str/bool/int/float", "sequences will be attributes"],
        a7=(1, 2, 3, 4, 5, 6),
        a5=55,
    )

    logging.warning("EXAMPLE #11")
    example_11_no_attributes(
        _MyObject("object won't be an attribute, but `msg`-attribute can be"),
        "arg1",
        "arg2",
        "arg3",
        a4={"dicts": "won't be", "added as": "attributes"},
        a6=["*homogeneous*", "str/bool/int/float", "sequences will be attributes"],
        a7=(1, 2, 3, 4, 5, 6),
        a5=55,
    )

    logging.warning("EXAMPLE #20")
    asyncio.get_event_loop().run_until_complete(example_20_async())
