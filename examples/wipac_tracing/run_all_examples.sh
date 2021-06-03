# Run all the example python files


files=`find examples/wipac_tracing/ -name '*.py' -a ! -name 'span_client_server_http.py'`
for f in $files; do python "$f"; done

python examples/wipac_tracing/span_client_server_http.py server &
python examples/wipac_tracing/span_client_server_http.py client &
wait

docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management &
python examples/wipac_tracing/span_peer_to_peer_example.py hank george &
python examples/wipac_tracing/span_peer_to_peer_example.py george hank &
wait
docker stop rabbitmq
