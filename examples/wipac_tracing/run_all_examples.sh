# Run all the example python files


files=`find examples/wipac_tracing/ -name '*.py' -a ! -name 'span_client_server_http.py'`
for f in $files; do python "$f"; done

python examples/wipac_tracing/span_client_server_http.py server &
python examples/wipac_tracing/span_client_server_http.py client &
wait
