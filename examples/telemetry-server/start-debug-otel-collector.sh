#!/usr/bin/env bash
# start-debug-otel-collector.sh
# Start an OpenTelemetry Collector for debugging purposes

# start the containers that provide the telemetry service
echo "Starting OpenTelemetry Collector (Debug)"

docker run \
    --name otel-collector \
    --publish 55680:55680 \
    --volume $(pwd)/debug-otel-collector.yaml:/etc/debug-otel-collector.yaml \
    otel/opentelemetry-collector:latest --config=/etc/debug-otel-collector.yaml

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping OpenTelemetry Collector (Debug)"
docker rm -f otel-collector
