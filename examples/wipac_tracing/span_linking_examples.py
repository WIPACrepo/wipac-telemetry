"""Example script for the spanned() decorator utilizing span-linking."""


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


class Request:
    """An example request object."""

    def __init__(self, message: str, span: wtt.Span, urgent: bool) -> None:
        self.message = message
        self.span_link: wtt.Link = wtt.make_link(
            span, "Request", {"type": "message", "urgent": urgent}
        )
        self.span_link_2: Optional[wtt.Link] = None
        self.id = random.randint(0, 90000)
        self.urgent = urgent


class Server:
    """An example server interface."""

    def __init__(self) -> None:
        pass

    @wtt.spanned(
        links=[
            "request.span_link",
            "request.span_link_2",
        ],  # span_link_2 will be ignored if `None`
        these=["request.message", "request.id", "request.urgent"],
    )
    def incoming(self, request: Request) -> None:
        """Handle an incoming message."""
        print(request.message)
        for i in reversed(range(4)):
            print(f"{i+1}...")
            time.sleep(0.5)
        print("Done")


class Client:
    """An example client interface."""

    def __init__(self, server: Server) -> None:
        self.server = server

    @wtt.spanned(these=["urgent"])
    def send(self, message: str, urgent: bool = False, delay: int = 0) -> None:
        """Send request to server."""
        time.sleep(delay)
        self.server.incoming(Request(message, wtt.get_current_span(), urgent))


def example_1() -> None:
    """Demo span linking.

    Full use cases would be cross-processed and asynchronous.
    """
    server = Server()
    client = Client(server)
    client.send("Hello World!", delay=1)


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1")
    example_1()
