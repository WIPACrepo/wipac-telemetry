#!/usr/bin/env bash
# start-jaeger-opentelemetry.sh
# Start a Jaeger OpenTelemetry telemetry service in Docker

J_TAG=${J_TAG:="latest"}

# start the containers that provide the telemetry service
echo "Starting Telemetry Service: Jaeger OpenTelemetry (Please Wait...)"

docker run \
    --detach \
    --env "COLLECTOR_ZIPKIN_HOST_PORT=9411" \
    --name jaeger \
    --publish 5775:5775/udp \
    --publish 6831:6831/udp \
    --publish 6832:6832/udp \
    --publish 4317:55680 \
    --publish 5778:5778 \
    --publish 9411:9411 \
    --publish 13133:13133 \
    --publish 14268:14268 \
    --publish 14250:14250 \
    --publish 16686:16686 \
    jaegertracing/opentelemetry-all-in-one:${J_TAG}

docker run \
  --detach \
  --link jaeger:jaeger \
  --name hotrod \
  --publish 8080-8083:8080-8083 \
  --env "JAEGER_AGENT_HOST=jaeger" \
  jaegertracing/example-hotrod:latest all

echo "Telemetry Service Ready: Jaeger (hotrod-ui:8080) (web-ui:16686) (zipkin:9411) (otel:4317)"
echo ""
echo "Port   Protocol  Component  Function"
echo "5775   UDP       agent      accept zipkin.thrift over compact thrift protocol"
echo "6831   UDP       agent      accept jaeger.thrift over compact thrift protocol"
echo "6832   UDP       agent      accept jaeger.thrift over binary thrift protocol"
echo ""
echo "4317   gRPC      collector  OTLP receiver"
echo "5778   HTTP      agent      serve configs"
echo "9411   HTTP      collector  Zipkin compatible endpoint"
echo "14268  HTTP      collector  accept jaeger.thrift directly from clients"
echo "14250  HTTP      collector  accept model.proto"
echo ""
echo "13133  HTTP      query      Health Check"
echo "16686  HTTP      query      serve frontend"

# wait for Ctrl-C to stop the telemetry service
( trap exit SIGINT ; read -r -d '' _ </dev/tty )

# stop and remove the containers that provide the telemetry service
echo "Stopping Telemetry Service: Jaeger OpenTelemetry"
docker rm -f hotrod jaeger
