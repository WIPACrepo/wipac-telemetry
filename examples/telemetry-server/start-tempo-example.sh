#!/usr/bin/env bash
# start-tempo-example.sh
# Start an example Grafana Tempo telemetry service in Docker

# start the containers that provide the telemetry service
echo "Starting Telemetry Service Example: Grafana Tempo (Please Wait...)"

# see: https://geekflare.com/grafana-tempo-intro/
# see: https://grafana.com/docs/tempo/latest/configuration/#distributor
docker run \
    --detach \
    --name tempo \
    --publish 3100:3100 \
    --publish 14268:14268 \
    --volume $(pwd)/tempo.yaml:/etc/tempo-local.yaml \
    --volume $(pwd)/example-data/tempo:/tmp/tempo \
    grafana/tempo:latest -config.file=/etc/tempo-local.yaml

docker run \
    --detach \
    --env "JAEGER_COLLECTOR_URL=http://tempo:14268" \
    --env "TOPOLOGY_FILE=/etc/load-generator.json" \
    --link tempo:tempo \
    --name synthetic-load-generator \
    --volume $(pwd)/etc/load-generator.json:/etc/load-generator.json \
    omnition/synthetic-load-generator:1.0.25

docker run \
    --detach \
    --link tempo:tempo \
    --name prometheus \
    --publish 9090:9090 \
    --volume $(pwd)/etc/prometheus.yaml:/etc/prometheus.yaml \
    prom/prometheus:latest

docker run \
    --detach \
    --env "GF_AUTH_ANONYMOUS_ENABLED=true" \
    --env "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin" \
    --env "GF_AUTH_DISABLE_LOGIN_FORM=true" \
    --name ui \
    --publish 3000:3000 \
    --volume $(pwd)/example-data/dashboards-provisioning:/etc/grafana/provisioning/dashboards \
    --volume $(pwd)/example-data/datasources:/etc/grafana/provisioning/datasources \
    --volume $(pwd)/tempo-mixin/out:/var/lib/grafana/dashboards \
    grafana/grafana:7.5.1

echo "Telemetry Service Example Ready: Grafana Tempo (ui:3000) (tempo:14268)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service Example: Grafana Tempo"
docker rm -f ui prometheus synthetic-load-generator tempo
