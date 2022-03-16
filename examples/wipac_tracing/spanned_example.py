"""Example script for the spanned() decorator."""


import asyncio
import itertools as it
import logging
import os
import sys
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

import coloredlogs  # type: ignore[import]

if "examples" not in os.listdir():
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401


@wtt.spanned()
def example_1_with_no_args() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


class Example2:
    """An example with an class instance method."""

    @wtt.spanned()
    def example_2_instance_method(self) -> None:
        """Print and log simple message."""
        msg = "Hello World!"
        print(msg)
        logging.info(msg)


@wtt.spanned(wtt.SpanNamer("my-span"))
def example_3_with_name() -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@wtt.spanned()
def example_4_with_an_uncaught_error() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to raise a FileNotFoundError"
    print(msg)
    logging.info(msg)
    raise FileNotFoundError("My FileNotFoundError message")


@wtt.spanned()
def example_5_with_a_caught_error() -> None:
    """Print and log simple message."""
    msg = "Hello World! I'm about to catch my ValueError"
    print(msg)
    logging.info(msg)
    try:
        raise ValueError("My ValueError message")
    except ValueError as e:
        logging.info(f"I caught this: `{e}`")


@wtt.spanned()
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


@wtt.spanned(all_args=True)
def example_7_attributes_from_sig_vals(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, str]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[Tuple[int, ...]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@wtt.spanned(attributes={"my": 1, "attributes": 2})
def example_8_attributes_only_explicit(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, str]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[Tuple[int, ...]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@wtt.spanned(attributes={"my": 1, "attributes": 2}, all_args=True)
def example_9_attributes_explicit_and_args(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, str]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[Tuple[int, ...]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@wtt.spanned(attributes={"my": 1, "attributes": 2}, these=["a0", "a1", "a6", "a0.msg"])
def example_10_attributes_explicit_and_whitelisted_args(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, str]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[Tuple[int, ...]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@wtt.spanned()
def example_11_no_attributes(  # pylint: disable=W0613,C0103,R0913
    a0: _MyObject,
    a1: str,
    a2: str,
    a3: str = "",
    a4: Optional[Dict[str, str]] = None,
    a5: int = -1,
    a6: Optional[List[str]] = None,
    a7: Optional[Tuple[int, ...]] = None,
) -> None:
    """Print and log simple message."""
    msg = "Hello World!"
    print(msg)
    logging.info(msg)


@wtt.spanned()
async def example_20_async() -> None:
    """Print and log simple message."""

    @wtt.spanned()
    def _inner_sync() -> None:
        print("inner-sync function")

    @wtt.spanned()
    async def _inner_async() -> None:
        await asyncio.sleep(2)
        print("inner-async function")

    _inner_sync()
    await _inner_async()
    print("Done with async example.")


@wtt.spanned()
def example_30_iter_an_iterator_function() -> None:
    """Span an iterator (from a basic iterator function)."""

    @wtt.spanned(these=["name"])
    def _gen(name: str) -> Iterator[int]:
        # pylint: disable=invalid-name
        a, b = 0, 1
        for _ in range(5):
            ret = a
            a, b = b, a + b
            yield ret

    name = "function-return variable w/ loop"
    logging.debug(f"---{name}---")
    gen = _gen(name)
    for i, num in enumerate(gen):
        print(f"#{i} :: {num}")
        time.sleep(0.25)

    name = "function-return directly w/ loop"
    logging.debug(f"---{name}---")
    for i, num in enumerate(_gen(name)):
        print(f"#{i} :: {num}")
        time.sleep(0.25)

    @wtt.spanned()
    def wrap_manual_iter(gen: Iterator[int]) -> Any:
        # will record as "Error" for OpenTelemetry on StopIteration
        # but **NOT** on `gen`'s trace(s)
        return next(gen)

    name = "function-return variable w/ next()"
    logging.debug(f"---{name}---")
    # will record as "Error" for OpenTelemetry
    gen = _gen(name)
    for i in it.count(0):
        try:
            num = wrap_manual_iter(gen)
        except StopIteration:
            break
        print(f"#{i} :: {num}")
        time.sleep(0.25)


@wtt.spanned()
def example_31_iter_an_iterator_class() -> None:
    """Span an iterator (from an iterator class instance)."""

    class Fib:
        """Fibonacci iterator object."""

        def __init__(self, name: str, maximum: int) -> None:
            self.a, self.b = 0, 1  # pylint: disable=invalid-name
            self.max = maximum
            self.i = 0
            self.name = name

        @wtt.spanned(these=["self.name"])
        def __next__(self) -> int:
            if self.max == self.i:
                raise StopIteration
            return_value = self.a
            self.a, self.b = self.b, self.a + self.b
            self.i += 1
            return return_value

        @wtt.spanned()
        def __iter__(self) -> "Fib":
            return self

    name = "class-instance variable w/ loop"
    logging.debug(f"---{name}---")
    gen = Fib(name, 5)
    for i, num in enumerate(gen):
        print(f"#{i} :: {num}")
        time.sleep(0.25)

    name = "class-instance directly w/ loop"
    logging.debug(f"---{name}---")
    for i, num in enumerate(Fib(name, 5)):
        print(f"#{i} :: {num}")
        time.sleep(0.25)

    @wtt.spanned()
    def wrap_manual_iter(gen: Fib) -> Any:
        # will record as "Error" for OpenTelemetry on StopIteration
        # but **NOT** on __next__()'s trace
        return next(gen)

    name = "class-instance variable w/ next()"
    logging.debug(f"---{name}---")
    gen = Fib(name, 5)
    for i in it.count(0):
        try:
            num = wrap_manual_iter(gen)
        except StopIteration:
            break
        print(f"#{i} :: {num}")
        time.sleep(0.25)


@wtt.spanned()
async def example_32_iter_an_async_iterator_class() -> None:
    """Span an iterator (from an iterator class instance)."""

    class Fib:
        """Fibonacci iterator object."""

        def __init__(self, name: str, maximum: int) -> None:
            self.a, self.b = 0, 1  # pylint: disable=invalid-name
            self.max = maximum
            self.i = 0
            self.name = name

        @wtt.spanned(these=["self.name"])
        async def __anext__(self) -> int:
            if self.max == self.i:
                raise StopAsyncIteration
            return_value = self.a
            self.a, self.b = self.b, self.a + self.b
            self.i += 1
            return return_value

        @wtt.spanned()
        def __aiter__(self) -> "Fib":
            return self

    name = "async class-instance variable w/ loop"
    logging.debug(f"---{name}---")
    gen = Fib(name, 5)
    i = 0
    async for num in gen:
        print(f"#{i} :: {num}")
        time.sleep(0.25)
        i += 1

    name = "async class-instance directly w/ loop"
    logging.debug(f"---{name}---")
    i = 0
    async for num in Fib(name, 5):
        print(f"#{i} :: {num}")
        time.sleep(0.25)
        i += 1

    @wtt.spanned()
    async def wrap_manual_iter(gen: Fib) -> Any:
        # will record as "Error" for OpenTelemetry on StopAsyncIteration
        # but **NOT** on __anext__()'s trace
        return await gen.__anext__()

    name = "async class-instance variable w/ __anext__()"
    logging.debug(f"---{name}---")
    gen = Fib(name, 5)
    for i in it.count(0):
        try:
            num = await wrap_manual_iter(gen)
        except StopAsyncIteration:
            break
        print(f"#{i} :: {num}")
        time.sleep(0.25)


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

    logging.warning("EXAMPLE #20 - NESTED ASYNC")
    asyncio.get_event_loop().run_until_complete(example_20_async())

    logging.warning("EXAMPLE #30 - ITERATOR FUNCTION")
    example_30_iter_an_iterator_function()

    logging.warning("EXAMPLE #31 - ITERATOR CLASS")
    example_31_iter_an_iterator_class()

    logging.warning("EXAMPLE #32 - ASYNC ITERATOR CLASS")
    asyncio.get_event_loop().run_until_complete(
        example_32_iter_an_async_iterator_class()
    )
