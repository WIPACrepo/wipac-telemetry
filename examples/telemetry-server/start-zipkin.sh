#!/usr/bin/env bash
# start-zipkin.sh
# Start a Zipkin OpenTelemetry telemetry service in Docker

# ensure that we're being run from the correct spot for volume mounts
CHECK_SCRIPT_HERE=$(which start-tempo.sh)
if [ -z "$CHECK_SCRIPT_HERE" ]; then
   echo "Please run $(basename $0) from the directory $(pwd)/$(dirname $0)"
   exit 1
fi

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Zipkin OpenTelemetry (Please Wait...)"

docker run \
    --detach \
    --name zipkin \
    --publish 9411:9411 \
    --restart always \
    openzipkin/zipkin:latest

docker run \
    --detach \
    --link zipkin:zipkin \
    --name otel-collector \
    --publish 4317:4317 \
    --publish 13133:13133 \
    --volume $(pwd)/otel-collector-zipkin.yaml:/etc/otel-collector-zipkin.yaml \
    otel/opentelemetry-collector:latest --config=/etc/otel-collector-zipkin.yaml

docker run \
    --detach \
    --link zipkin:zipkin \
    --name jaeger \
    --publish 6831:6831 \
    --publish 6832:6832 \
    --publish 13134:13133 \
    --publish 14250:14250 \
    --publish 14268:14268 \
    --volume $(pwd)/otel-collector-zipkin-jaeger.yaml:/etc/otel-collector-zipkin-jaeger.yaml \
    otel/opentelemetry-collector:latest --config=/etc/otel-collector-zipkin-jaeger.yaml

sleep 1

docker run \
  --detach \
  --link jaeger:jaeger \
  --name hotrod \
  --publish 8080-8083:8080-8083 \
  --env "JAEGER_AGENT_HOST=jaeger" \
  jaegertracing/example-hotrod:latest all

echo "Telemetry Service Ready: Zipkin (web-ui:9411) (zipkin:9411) (otel:4317) (hotrod-ui:8080)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Zipkin OpenTelemetry"
docker rm -f hotrod jaeger otel-collector zipkin
