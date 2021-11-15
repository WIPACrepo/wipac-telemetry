"""Examples for spanned() decorator with http-based client/server tracing."""


import http.client
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import coloredlogs  # type: ignore[import]

if "examples" not in os.listdir():
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401

ADDRESS = "127.0.0.1"
PORT = 2000

########################################################################################


@wtt.spanned(
    span_namer=wtt.SpanNamer(literal_name="TheBestClient"), kind=wtt.SpanKind.CLIENT
)
def client() -> None:
    """Run HTTP client."""
    logging.info("Example HTTP Client with 'kind=SpanKind.CLIENT'")

    logging.debug("http client is starting...")
    time.sleep(0.5)

    conn = http.client.HTTPConnection(ADDRESS, PORT)  # create a connection
    logging.debug("http client is running...")
    time.sleep(0.5)

    for msg in ["ham", "cheese", "bacon", "nails"]:
        wtt.add_event(
            "Outgoing Server Request",
            {"message": msg, "address": ADDRESS, "port": PORT},
        )
        conn.request("GET", msg, headers=wtt.inject_span_carrier())

        # get response from server
        rsp = conn.getresponse()
        data_received = str(rsp.read())

        wtt.add_event(
            "Incoming Server Response",
            {"message": data_received, "status": rsp.status, "reason": rsp.reason},
        )

        # print server response and data
        logging.debug(rsp.status)
        logging.debug(rsp.reason)
        logging.debug(data_received)

        time.sleep(1)

    conn.close()


########################################################################################


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTPRequestHandler class."""

    @wtt.spanned(
        span_namer=wtt.SpanNamer(use_this_arg="self.command"),
        kind=wtt.SpanKind.SERVER,
        carrier="self.headers",
    )
    def do_GET(self) -> None:  # pylint: disable=invalid-name
        """Handle GET command."""
        logging.info("Example HTTP Server Handler with 'kind=SpanKind.SERVER'")

        all_responses = {
            "ham": "ham sandwich!",
            "cheese": "cheese sandwich!",
            "bacon": "BLT!",
        }

        if self.path in all_responses:
            self.send_response(200)

            # send header first
            self.send_header("Content-type", "text-html")
            self.end_headers()

            # send file content to client
            self.wfile.write(all_responses[self.path].encode())

        else:
            self.send_error(404, "Ingredient not found!")

            logging.critical("Server shutting down (to end testing)")
            sys.exit(0)


def server() -> None:
    """Run HTTP server."""
    logging.info("Example HTTP Server Application")

    logging.debug("http server is starting...")
    time.sleep(0.5)

    server_address = (ADDRESS, PORT)
    httpd = HTTPServer(server_address, HTTPRequestHandler)

    logging.debug("http server is running...")
    time.sleep(0.5)

    httpd.serve_forever()


########################################################################################


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    try:
        {"client": client, "server": server}[sys.argv[1]]()
    except (IndexError, KeyError):
        logging.debug("enter either 'client' or 'server'")
        sys.exit(1)
