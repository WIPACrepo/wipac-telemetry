#!/usr/bin/env bash
# start-tempo.sh
# Start a Grafana Tempo telemetry service in Docker

# ensure that we're being run from the correct spot for volume mounts
CHECK_SCRIPT_HERE=$(which start-tempo.sh)
if [ -z "$CHECK_SCRIPT_HERE" ]; then
   echo "Please run $(basename $0) from the directory $(pwd)/$(dirname $0)"
   exit 1
fi

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Grafana Tempo (Please Wait...)"

# see: https://geekflare.com/grafana-tempo-intro/
# see: https://grafana.com/docs/tempo/latest/configuration/#distributor
mkdir -p /tmp/tempo-data
docker run \
    --detach \
    --name tempo \
    --publish 3100:3100 \
    --publish 4317:55680 \
    --publish 9411:9411 \
    --publish 14268:14268 \
    --publish 55681:55681 \
    --volume $(pwd)/tempo.yaml:/etc/tempo-local.yaml \
    --volume /tmp/tempo-data:/tmp/tempo \
    grafana/tempo:latest -config.file=/etc/tempo-local.yaml

docker run \
    --detach \
    --link tempo:tempo \
    --name ui \
    --publish 16686:16686 \
    --volume $(pwd)/tempo-query.yaml:/etc/tempo-query.yaml \
    grafana/tempo-query:latest --grpc-storage-plugin.configuration-file=/etc/tempo-query.yaml

docker run \
    --detach \
    --link tempo:tempo \
    --name otel-collector \
    --volume $(pwd)/otel-collector.yaml:/etc/otel-collector.yaml \
    otel/opentelemetry-collector:0.27.0 --config=/etc/otel-collector.yaml

docker run \
    --detach \
    --link tempo:tempo \
    --name prometheus \
    --publish 9090:9090 \
    --volume $(pwd)/prometheus.yaml:/etc/prometheus.yaml \
    prom/prometheus:latest --config.file=/etc/prometheus.yaml

docker run \
    --detach \
    --env "GF_AUTH_ANONYMOUS_ENABLED=true" \
    --env "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin" \
    --env "GF_AUTH_DISABLE_LOGIN_FORM=true" \
    --link prometheus:prometheus \
    --link tempo:tempo \
    --name grafana \
    --publish 3000:3000 \
    --volume $(pwd)/grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml \
    grafana/grafana:7.5.7

docker run \
    --detach \
    --link tempo:tempo \
    --name jaeger \
    --publish 6831:6831 \
    --publish 6832:6832 \
    --publish 13134:13133 \
    --publish 14250:14250 \
    --volume $(pwd)/otel-collector-tempo-jaeger.yaml:/etc/otel-collector-tempo-jaeger.yaml \
    otel/opentelemetry-collector:latest --config=/etc/otel-collector-tempo-jaeger.yaml

sleep 1

#    --detach \
docker run \
  --link jaeger:jaeger \
  --name hotrod \
  --publish 8080-8083:8080-8083 \
  --env "JAEGER_AGENT_HOST=jaeger" \
  jaegertracing/example-hotrod:latest all &

echo "Telemetry Service Ready: Grafana Tempo (web-ui:3000) (otel:4317) (hotrod-ui:8080)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Grafana Tempo"
docker rm -f hotrod jaeger grafana prometheus otel-collector ui tempo
