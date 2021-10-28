# wipac-telemetry-prototype
Prototype for WIPAC Telemetry : Monitoring/Tracing Applications, Supporting Infrastructures, and Services

## Running with Local Collector Service UI (Jaegar)
1. `cd examples/telemetry-server/jaeger-production && ./start-jaeger-production.sh`
1. Open new terminal:
1. `export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces`
1. Run script(s) and/or module(s)
1. Go to <http://localhost:16686/>