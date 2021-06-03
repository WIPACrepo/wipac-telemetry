"""Examples for spanned() decorator with peer-to-peer based tracing."""


import logging
import os
import sys
import time

import coloredlogs  # type: ignore[import]
import pika

if "examples" not in os.listdir():
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401

ADDRESS = "localhost"  # "127.0.0.1"
PORT = 2000

LOGGER = logging.getLogger(__name__)


########################################################################################


def send(friend: str, myself: str) -> None:
    """Send a message."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=ADDRESS))
    channel = connection.channel()

    channel.queue_declare(queue=friend)

    msg = f"Hey {friend}, I'm {myself}"
    channel.basic_publish(exchange="", routing_key=friend, body=msg)
    print(f" [x] Sent '{msg}'")
    connection.close()


def receive(myself: str) -> str:
    """Receive a message."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=ADDRESS))
    channel = connection.channel()

    channel.queue_declare(queue=myself)

    def callback(ch, method, properties, body: bytes) -> None:
        print(f" [x] Received '{str(body)}'")
        channel.stop_consuming()

    channel.basic_consume(queue=myself, on_message_callback=callback, auto_ack=True)

    # print(" [*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


########################################################################################


def main() -> None:
    """Do the things."""
    try:
        myself, friend = sys.argv[1], sys.argv[2]
    except (IndexError, KeyError):
        LOGGER.debug("enter name of 'friend' and 'me'")
        sys.exit(1)

    time.sleep(1)
    send(friend, myself)
    time.sleep(1)
    receive(myself)

    print("Done.")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG", logger=LOGGER)

    main()
