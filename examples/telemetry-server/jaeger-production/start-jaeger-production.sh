#!/usr/bin/env bash
# start-jaeger-production.sh
# Start a Jaeger OpenTelemetry telemetry service in Docker

# ensure that we're being run from the correct spot for volume mounts
CHECK_SCRIPT_HERE=$(which start-jaeger-production.sh)
if [ -z "$CHECK_SCRIPT_HERE" ]; then
   echo "Please run $(basename $0) from the directory $(pwd)/$(dirname $0)"
   exit 1
fi

ES_TAG=${ES_TAG:="latest"}
J_TAG=${J_TAG:="latest"}
OT_TAG=${OT_TAG:="latest"}

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Jaeger OpenTelemetry (Please Wait...)"

# see: https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-dev-mode
    # docker.elastic.co/elasticsearch/elasticsearch:${ES_TAG}
# see: https://hub.docker.com/r/bitnami/elasticsearch
#   sudo sysctl -w vm.max_map_count=262144
docker run \
    --detach \
    --env "discovery.type=single-node" \
    --memory="2g" \
    --name elasticsearch \
    --publish 9200:9200 \
    --publish 9300:9300 \
    --rm \
    bitnami/elasticsearch:${ES_TAG}

echo "Waiting for ElasticSearch cluster to start up (Please Wait...)"
sleep 30

docker run \
    --detach \
    --env "SPAN_STORAGE_TYPE=elasticsearch" \
    --env "ES_SERVER_URLS=http://elasticsearch:9200" \
    --link elasticsearch:elasticsearch \
    --name jaeger-collector \
    --publish 9411:9411 \
    --publish 14250:14250 \
    --publish 14268:14268 \
    --publish 14269:14269 \
    --rm \
    jaegertracing/jaeger-collector:${J_TAG}

docker run \
    --detach \
    --link jaeger-collector:jaeger-collector \
    --name jaeger-agent \
    --publish 5775:5775/udp \
    --publish 5778:5778 \
    --publish 6831:6831/udp \
    --publish 6832:6832/udp \
    --publish 14271:14271 \
    --rm \
    jaegertracing/jaeger-agent:${J_TAG} \
    --reporter.grpc.host-port=jaeger-collector:14250

docker run \
    --detach \
    --env "SPAN_STORAGE_TYPE=elasticsearch" \
    --env "ES_SERVER_URLS=http://elasticsearch:9200" \
    --link elasticsearch:elasticsearch \
    --name jaeger-query \
    --publish 16685:16685 \
    --publish 16686:16686 \
    --publish 16687:16687 \
    --rm \
    jaegertracing/jaeger-query:${J_TAG}

docker run \
   --detach \
    --link jaeger-collector:jaeger-collector \
    --name otel-collector \
    --publish 4317:4317 \
    --publish 13133:13133 \
    --publish 55678-55679:55678-55679 \
    --rm \
    --volume $(pwd)/otel-collector.yaml:/etc/otel-collector.yaml \
    otel/opentelemetry-collector:${OT_TAG} \
    --config=/etc/otel-collector.yaml

docker run \
    --detach \
    --env "JAEGER_AGENT_HOST=jaeger-agent" \
    --env "JAEGER_AGENT_PORT=6831" \
    --link jaeger-agent:jaeger-agent \
    --name hotrod \
    --publish 8080-8083:8080-8083 \
    --rm \
    jaegertracing/example-hotrod:latest all

echo "Telemetry Service Ready: Jaeger (hotrod-ui:8080) (jaeger:14250) (otlp:4317) (web-ui:16686) (zipkin:9411)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Jaeger OpenTelemetry"
docker rm -f elasticsearch hotrod jaeger-agent jaeger-collector jaeger-query otel-collector
