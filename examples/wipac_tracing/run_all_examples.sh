# Run all the example python files

export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"

files=`find examples/wipac_tracing/ -name '*.py' -a ! -name 'span_client_server_http.py' -a ! -name 'span_peer_to_peer_example.py'`
for f in $files; do python "$f"; done

python examples/wipac_tracing/span_client_server_http.py server &
python examples/wipac_tracing/span_client_server_http.py client &
wait

python examples/wipac_tracing/span_peer_to_peer_example.py hank george &
python examples/wipac_tracing/span_peer_to_peer_example.py george hank &
wait