#!/usr/bin/env bash
# start-skywalking.sh
# Start an Apache Skywalking telemetry service in Docker

ES_TAG=${ES_TAG:="7.12.1"}
SW_TAG=${SW_TAG:="8.5.0"}

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Apache Skywalking (Please Wait...)"

# see: https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-dev-mode
docker run \
    --detach \
    --env "discovery.type=single-node" \
    --memory="2g" \
    --name elasticsearch \
    --publish 9200:9200 \
    --publish 9300:9300 \
    --restart always \
    docker.elastic.co/elasticsearch/elasticsearch:${ES_TAG}

sleep 15

docker run \
    --detach \
    --env "SW_STORAGE=elasticsearch7" \
    --env "SW_STORAGE_ES_CLUSTER_NODES=elasticsearch:9200" \
    --env "SW_HEALTH_CHECKER=default" \
    --env "SW_TELEMETRY=prometheus" \
    --link elasticsearch:elasticsearch \
    --name oap \
    --publish 11800:11800 \
    --publish 12800:12800 \
    --restart always \
    apache/skywalking-oap-server:${SW_TAG}-es7

docker run \
    --detach \
    --env "SW_OAP_ADDRESS=oap:12800" \
    --link oap:oap \
    --name ui \
    --publish 8080:8080 \
    --restart always \
    apache/skywalking-ui:${SW_TAG}

sleep 15

echo "Telemetry Service Ready: Apache Skywalking (ui:8080) (oap:12800)"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Apache Skywalking"
docker rm -f ui oap elasticsearch
