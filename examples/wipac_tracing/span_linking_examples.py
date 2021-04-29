"""Example script for the spanned() decorator utilizing span-linking."""


import logging
import os
import random
import sys
import time
from typing import cast

import coloredlogs  # type: ignore[import]

if not os.getcwd().endswith("/wipac-telemetry-prototype"):
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
from wipac_telemetry import tracing  # noqa: E402 # pylint: disable=C0413,E0401
from wipac_telemetry.tracing.tools import (  # noqa: E402 # pylint: disable=C0413
    OptSpan,
    Span,
)


class Request:
    """An example request object."""

    def __init__(self, message: str, span: Span) -> None:
        self.message = message
        self.span = span
        self.id = random.randint(0, 90000)


class Server:
    """An example server interface."""

    def __init__(self) -> None:
        pass

    @tracing.tools.spanned(
        links=["request.span"], these=["request.message", "request.id"]
    )
    def incoming(self, request: Request) -> None:
        """Handle an incoming message."""
        print(request.message)
        for i in reversed(range(4)):
            print(f"{i+1}...")
            time.sleep(1)
        print("Done")


class Client:
    """An example client interface."""

    def __init__(self, server: Server) -> None:
        self.server = server

    @tracing.tools.spanned(inject=True)
    def send(self, message: str, span: OptSpan = None) -> None:
        """Send request to server."""
        span = cast(Span, span)
        self.server.incoming(Request(message, span))
        span.end()


def example_1() -> None:
    """Demo span linking.

    Full use cases would be cross-processed and asynchronous.
    """
    server = Server()
    client = Client(server)
    client.send("Hello World!")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    logging.warning("EXAMPLE #1")
    example_1()
