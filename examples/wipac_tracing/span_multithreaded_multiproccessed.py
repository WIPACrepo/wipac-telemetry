"""Examples for spanned() decorator with multi-threaded/processed tracing."""

# pylint: disable=protected-access


import logging
import os
import sys
import time
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any, Dict, List

import coloredlogs  # type: ignore[import]

if "examples" not in os.listdir():
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401

########################################################################################


@wtt.spanned()
def example_00_threads_incorrect(n_threads: int) -> None:
    """Run multiple independent threads, INCORRECTLY.

    Spanning an in-thread function will not inherit ANYTHING. The
    resulting span is completely not related in any way to the
    *intended* parent.

    Don't do this!
    """
    outter_span = wtt.get_current_span()

    @wtt.spanned(all_args=True)
    def thread_work(worker: int) -> int:
        """Do thread's work."""
        assert outter_span.is_recording()  # surprising? this is b/c of shared memory
        assert wtt.get_current_span().is_recording()  # as expected
        assert outter_span != wtt.get_current_span()  # good

        # NOT GOOD!
        assert not wtt.get_current_span()._parent  # type: ignore[attr-defined]

        # # # #
        time.sleep(1)
        return worker

    futures: List[Future] = []  # type: ignore[type-arg]
    with ThreadPoolExecutor() as pool:
        for i in range(n_threads):
            futures.append(pool.submit(thread_work, i))

    for worker in as_completed(futures):
        ret = worker.result()
        print(f"Returned Worker #{ret}")


@wtt.spanned()
def example_01_threads_incorrect(n_threads: int) -> None:
    """Run multiple independent threads, INCORRECTLY.

    A non-spanned in-thread function won't be spanned by its *intended*
    parent.

    Don't do this!
    """
    outter_span = wtt.get_current_span()

    def thread_work(worker: int, carrier: Dict[str, Any]) -> int:
        """Do thread's work."""
        assert outter_span.is_recording()  # surprising? this is b/c of shared memory
        assert not wtt.get_current_span().is_recording()  # BAD!
        assert outter_span != wtt.get_current_span()  # good
        # assert wtt.get_current_span()._parent # (n/a b/c not recording)
        # # # #
        print(carrier)
        time.sleep(1)
        # shared memory allows this -- but not a great idea logically...
        outter_span.add_event("I'm", {"A": "Thread"})
        return worker

    futures: List[Future] = []  # type: ignore[type-arg]
    with ThreadPoolExecutor() as pool:
        for i in range(n_threads):
            carrier = wtt.inject_span_carrier()
            print(carrier)
            futures.append(pool.submit(thread_work, i, carrier))

    for worker in as_completed(futures):
        ret = worker.result()
        wtt.add_event("Worker Join", {"worker-id": ret, "type": "thread"})
        print(f"Returned Worker #{ret}")


@wtt.spanned()
def example_02_threads_incorrect(n_threads: int) -> None:
    """Run multiple independent threads, INCORRECTLY.

    A re-spanned in-thread function may work, but is NOT SAFE. There's a
    race condition: a parent process/thread may end the span before the
    child thread uses it, or visa-versa. It's not a good idea.

    Don't do this!
    """
    outter_span = wtt.get_current_span()

    # even with `wtt.SpanBehavior.DONT_END`, this isn't a good idea
    @wtt.respanned("span", wtt.SpanBehavior.END_ON_EXIT)
    def thread_work(worker: int, span: wtt.Span) -> int:
        """Do thread's work."""
        assert span == outter_span == wtt.get_current_span()
        assert outter_span.is_recording()  # sure
        assert wtt.get_current_span().is_recording()  # as expected
        assert outter_span == wtt.get_current_span()  # as expected
        assert not wtt.get_current_span()._parent  # type: ignore[attr-defined]
        # # # #
        # print(carrier)
        time.sleep(1)
        # shared memory allows this -- but not a great idea logically...
        outter_span.add_event("I'm", {"A": "Thread"})
        return worker

    futures: List[Future] = []  # type: ignore[type-arg]
    with ThreadPoolExecutor() as pool:
        for i in range(n_threads):
            # carrier = wtt.inject_span_carrier()
            # print(carrier)
            futures.append(pool.submit(thread_work, i, outter_span))

    for worker in as_completed(futures):
        ret = worker.result()
        wtt.add_event("Worker Join", {"worker-id": ret, "type": "thread"})
        print(f"Returned Worker #{ret}")


########################################################################################


@wtt.spanned()
def example_10_threads(n_threads: int) -> None:
    """Run multiple independent threads, with a common carrier."""
    outter_span = wtt.get_current_span()

    @wtt.spanned(all_args=True, carrier="carrier")
    def thread_work(worker: int, carrier: Dict[str, Any]) -> int:
        """Do thread's work."""
        assert outter_span.is_recording()  # surprising? this is b/c of shared memory
        assert wtt.get_current_span().is_recording()  # as expected
        assert outter_span != wtt.get_current_span()  # good
        assert wtt.get_current_span()._parent  # type: ignore[attr-defined]  # GREAT!
        # # # #
        print(carrier)
        time.sleep(1)
        return worker

    futures: List[Future] = []  # type: ignore[type-arg]
    with ThreadPoolExecutor() as pool:
        for i in range(n_threads):
            carrier = wtt.inject_span_carrier()
            print(carrier)
            futures.append(pool.submit(thread_work, i, carrier))

    for worker in as_completed(futures):
        ret = worker.result()
        wtt.add_event("Worker Join", {"worker-id": ret, "type": "thread"})
        print(f"Returned Worker #{ret}")


########################################################################################


@wtt.spanned(all_args=True, carrier="carrier")
def process_work(worker: int, carrier: Dict[str, Any]) -> int:
    """Do child process's work."""
    print(carrier)
    time.sleep(1)
    return worker


@wtt.spanned()
def example_20_processes(n_threads: int) -> None:
    """Run multiple independent process, with a common carrier."""
    futures: List[Future] = []  # type: ignore[type-arg]
    with ProcessPoolExecutor() as pool:
        for i in range(n_threads):
            carrier = wtt.inject_span_carrier()
            print(carrier)
            futures.append(pool.submit(process_work, i, carrier))

    for worker in as_completed(futures):
        ret = worker.result()
        wtt.add_event("Worker Join", {"worker-id": ret, "type": "process"})
        print(f"Returned Worker #{ret}")


########################################################################################


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    # MULTI-THREADING

    logging.warning("EXAMPLE #00 - Threaded Incorrectly")
    example_00_threads_incorrect(3)

    logging.warning("EXAMPLE #01 - Threaded Incorrectly")
    example_01_threads_incorrect(3)

    logging.warning("EXAMPLE #02 - Threaded Incorrectly")
    example_02_threads_incorrect(3)

    logging.warning("EXAMPLE #10 - Threaded with Carrier")
    example_10_threads(3)

    # MULTI-PROCESSING

    logging.warning("EXAMPLE #20 - Processes with Carrier")
    example_20_processes(3)

    # At this point you may be wondering,
    # "Well what happens if I use 'respanned' with multi-processing?"
    # Bad things, bad things will happen: inconsistent sem-lock
    # errors/timeouts, hanging processes, etc.
