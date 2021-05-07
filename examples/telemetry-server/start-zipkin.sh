#!/usr/bin/env bash
# start-zipkin.sh
# Start a Zipkin telemetry service in Docker

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Zipkin (Please Wait...)"

docker run \
    --detach \
    --name zipkin \
    --publish 9411:9411 \
    --restart always \
    openzipkin/zipkin

echo "Telemetry Service Ready: Zipkin (ui:9411) (zipkin:9411)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Zipkin"
docker rm -f zipkin
