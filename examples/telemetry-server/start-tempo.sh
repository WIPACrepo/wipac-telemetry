#!/usr/bin/env bash
# start-tempo.sh
# Start a Grafana Tempo telemetry service in Docker

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Grafana Tempo (Please Wait...)"

# see: https://geekflare.com/grafana-tempo-intro/
# see: https://grafana.com/docs/tempo/latest/configuration/#distributor
docker run \
    --detach \
    --name tempo \
    --publish 3100:3100 \
    --publish 55680:55680 \
    --volume $(pwd)/tempo.yaml:/etc/tempo-local.yaml \
    grafana/tempo:latest -config.file=/etc/tempo-local.yaml

docker run \
    --detach \
    --link tempo:tempo \
    --name ui \
    --publish 16686:16686 \
    --volume $(pwd)/tempo-query.yaml:/etc/tempo-query.yaml \
    grafana/tempo-query:latest --grpc-storage-plugin.configuration-file=/etc/tempo-query.yaml

echo "Telemetry Service Ready: Grafana Tempo (ui:16686) (tempo:55680)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Grafana Tempo"
docker rm -f ui tempo
