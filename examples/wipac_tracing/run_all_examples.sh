#!/bin/bash

# Run all the example python files

set -x
set -e

export OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT:="http://localhost:4318/v1/traces"}
# export WIPACTEL_EXPORT_STDOUT=${WIPACTEL_EXPORT_STDOUT:="TRUE"}

divider=`printf '=%.0s' {1..100}`

for fpath in `find examples/wipac_tracing/ -maxdepth 1 -name '*.py'`; do
	fname=`basename $fpath`
	if [ $fname == "span_client_server_http.py" ] || [ $fname == "span_peer_to_peer_example.py" ]; then
		continue
	fi
	echo $divider
	echo "$fpath"
	python "$fpath"
done

echo $divider
python -m examples.wipac_tracing.a_traced_module

echo $divider
echo "examples/wipac_tracing/span_client_server_http.py"
python examples/wipac_tracing/span_client_server_http.py server &
python examples/wipac_tracing/span_client_server_http.py client &
wait -n
wait -n

echo $divider
echo "examples/wipac_tracing/span_peer_to_peer_example.py"
python examples/wipac_tracing/span_peer_to_peer_example.py hank george &
python examples/wipac_tracing/span_peer_to_peer_example.py george hank &
wait -n
wait -n
