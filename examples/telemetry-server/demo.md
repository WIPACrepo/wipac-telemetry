# demo.md
Showing off traces and logs in visualization tools

## Visualize Traces

### Apache Skywalking
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetry-prototype/examples/telemetry-server

2. Run script to set up local Docker environment

    ./start-skywalking.sh

3. ????

4. PROFIT!

Seriously, Apache Skywalking looks very cool, but it's a Chinese project with
non-native English documentation. At times, this makes it difficult to follow,
and getting an OTEL collector set up has not been easy.

It's probably worth investing some time in, but it will require a deeper dive.

### Grafana Tempo
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetry-prototype/examples/telemetry-server

2. Run script to set up local Docker environment

    ./start-tempo.sh

3. Open browser to Grafana Web UI

    google-chrome --new-window http://localhost:3000/

4. Select Explore (compass) from the left hand side

5. Select Tempo in the drop-down at the top (should be default)

6. Look for a "trace_id" in the trace generation logs

    2021-06-14 01:35:55 bluebird root[23384] DEBUG b'cheese sandwich!'
    2021-06-14 01:35:56 bluebird root[23383] INFO Example HTTP Server Handler with 'kind=SpanKind.SERVER'
    127.0.0.1 - - [14/Jun/2021 01:35:56] "GET bacon HTTP/1.1" 200 -
    {
        "name": "HTTPRequestHandler.do_GET",
        "context": {
            "trace_id": "0x882ee09cef5f23a922344dcfdc8b1e23",
            "span_id": "0x76f96a5956dbd913",
            "trace_state": "[]"
        },

7. Copy the trace_id `882ee09cef5f23a922344dcfdc8b1e23` to the Trace ID field in the UI

8. Select the blue "Run Query" button in the upper right corner

### Jaeger UI (OpenTelemetry)
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetry-prototype

2. Run script to set up local Docker environment

    ./examples/telemetry-server/start-jaeger-opentelemetry.sh

3. Open browser to Web UI

    google-chrome --new-window http://localhost:16686/

### Zipkin
Although we have a `start-zipkin.sh` script, the wipac_tracing tools export
via console or OpenTelemetry. Sending traces via Zipkin is possible, but we're
not configured for it yet and I didn't find an easy OTEL -> Zipkin component
to set up.

## Generate Traces

### Jaeger HOTrod
TODO: Create a script for generating traces with Jaeger HOTrod

### wipac_telemetry run_all_examples.sh
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetry-prototype

2. Source Python virtual environment

    source env/bin/activate

3. Run script to generate traces (when desired)

    bash -x ./examples/wipac_tracing/run_all_examples.sh
