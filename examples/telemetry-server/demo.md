# demo.md
Showing off traces and logs in visualization tools

## Visualize Traces

### Apache Skywalking
Apache Skywalking does not support OpenTelemetry traces:
* https://github.com/apache/skywalking/issues/5884#issuecomment-732514234
* https://github.com/apache/skywalking/issues/6135#issuecomment-755036573

Their take is: Use OpenTelemetry collector to convert to Zipkin...
https://github.com/apache/skywalking/issues/6445

... which they consider an experimental reciever ...
https://skywalking.apache.org/docs/main/latest/en/setup/backend/backend-receivers/#zipkin-receiver

... and don't forget to enable Zipkin storage in ElasticSearch
https://skywalking.apache.org/docs/main/latest/en/setup/backend/backend-storage/#elasticsearch-7-with-zipkin-trace-extension

### Grafana Tempo
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetry/examples/telemetry-server

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

    cd ~/github/WIPACrepo/wipac-telemetry

2. Run script to set up local Docker environment

    ./examples/telemetry-server/start-jaeger-opentelemetry.sh

3. Open browser to HotROD Web UI

    google-chrome --new-window http://localhost:8080/

4. You can manually reach the Jaeger UI with this command

    google-chrome --new-window http://localhost:16686/

### Zipkin
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetry/examples/telemetry-server

2. Run script to set up local Docker environment

    ./start-zipkin.sh

3. Open browser to Zipkin Web UI

    google-chrome --new-window http://localhost:9411/zipkin/

4. Click the blue Run Query button



## Generate Traces

### Jaeger HotROD
* Run the Jaeger demo

### Synthetic Load
* Looked interesting; but the GitHub repository is archived and the tool is
no longer recommended.

    https://github.com/Omnition/synthetic-load-generator

The open issues make it seem like it's not quite OpenTelemetry compatible,
and my guess is the author didn't want to update it.

### wipac_telemetry run_all_examples.sh
1. Open terminal window

    cd ~/github/WIPACrepo/wipac-telemetrys

2. Source Python virtual environment

    source env/bin/activate

3. Run script to generate traces (when desired)

    bash -x ./examples/wipac_tracing/run_all_examples.sh
