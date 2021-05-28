"""Examples for spanned() decorator with multi-threaded/processed tracing."""


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
def example_00_threads_no_carrier(n_threads: int) -> None:
    """Run multiple independent threads, without a common carrier."""

    @wtt.spanned(all_args=True)
    def thread_work(worker: int) -> int:
        """Do thread's work."""
        time.sleep(1)
        return worker

    futures: List[Future] = []  # type: ignore[type-arg]
    with ThreadPoolExecutor() as pool:
        for i in range(n_threads):
            futures.append(pool.submit(thread_work, i))

    for worker in as_completed(futures):
        ret = worker.result()
        print(f"Returned Worker #{ret}")


########################################################################################


@wtt.spanned()
def example_10_threads(n_threads: int) -> None:
    """Run multiple independent threads, with a common carrier."""

    @wtt.spanned(all_args=True, carrier="carrier")
    def thread_work(worker: int, carrier: Dict[str, Any]) -> int:
        """Do thread's work."""
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

    logging.warning("EXAMPLE #0 - Threaded, No Carrier")
    example_00_threads_no_carrier(3)

    logging.warning("EXAMPLE #10 - Threaded with Carrier")
    example_10_threads(3)

    logging.warning("EXAMPLE #20 - Processes with Carrier")
    example_20_processes(3)
