"""Examples for spanned() decorator with peer-to-peer based tracing."""


import logging
import os
import random
import sys
import time

import coloredlogs  # type: ignore[import]
import pika  # type: ignore[import]

if "examples" not in os.listdir():
    raise RuntimeError("Script needs to be ran from root of repository.")

sys.path.append(".")
import wipac_telemetry.tracing_tools as wtt  # noqa: E402 # pylint: disable=C0413,E0401

ADDRESS = "localhost"  # "127.0.0.1"
PORT = 2000

LOGGER = logging.getLogger(f"{random.randint(0, 1000):04d}")


########################################################################################


@wtt.spanned(all_args=True, kind=wtt.SpanKind.PRODUCER)
def go_publish(
    another_span: wtt.Span,
    friend: str,
    myself: str,
    channel: pika.adapters.blocking_connection.BlockingChannel,
) -> None:
    """Publish a message."""
    msg = f"Hey {friend}, I'm {myself}"

    another_link = wtt.span_to_link(
        another_span,
        {
            "name": "another_span",
            "NOTE": "explicitly linking `another_span` isn't necessary, it's `producer-span`'s parent",
            "REASONING": "`another_span` is already automatically accessible via the `producer-span`'s `parent_id` pointer",
            "FURTHERMORE": "this is just an example of linking multiple spans :D",
        },
    )

    headers = wtt.inject_links_carrier(
        attrs={"name": "producer-span", "from": myself, "to": friend},
        addl_links=[another_link],
    )

    channel.basic_publish(
        exchange="",
        routing_key=friend,
        body=msg,
        properties=pika.BasicProperties(headers=headers),
    )

    LOGGER.debug(f" [x] Sent '{msg}'")


@wtt.spanned(all_args=True)
def send(friend: str, myself: str) -> None:
    """Send a message."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=ADDRESS))
    channel = connection.channel()

    channel.queue_declare(queue=friend)

    go_publish(wtt.get_current_span(), friend, myself, channel)
    connection.close()


########################################################################################


@wtt.spanned(
    kind=wtt.SpanKind.CONSUMER,
    these=["properties.headers.just-a-key"],
    carrier="properties.headers",
    carrier_relation=wtt.CarrierRelation.LINK,
)
def receive_callback(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    method: pika.spec.Basic.Deliver,
    properties: pika.spec.BasicProperties,
    body: bytes,
) -> None:
    """Handle received message."""
    LOGGER.debug(channel)
    LOGGER.debug(method)
    LOGGER.debug(properties)
    LOGGER.debug(properties.headers)
    LOGGER.debug(f" [x] Received '{str(body)}'")
    channel.stop_consuming()


@wtt.spanned(all_args=True)
def receive(myself: str) -> None:
    """Receive a message."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=ADDRESS))
    channel = connection.channel()

    channel.queue_declare(queue=myself)

    channel.basic_consume(
        queue=myself, on_message_callback=receive_callback, auto_ack=True
    )

    # print(" [*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


########################################################################################


@wtt.spanned(all_args=True)
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
    time.sleep(1)
    print("Done.")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")
    logging.getLogger("pika").setLevel(logging.WARNING)

    main()
