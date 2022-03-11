<!--- Top of README Badges (automated) --->
[![CircleCI](https://img.shields.io/circleci/build/github/WIPACrepo/wipac-telemetry)](https://app.circleci.com/pipelines/github/WIPACrepo/wipac-telemetry?branch=main&filter=all) [![PyPI](https://img.shields.io/pypi/v/wipac-telemetry)](https://pypi.org/project/wipac-telemetry/) [![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/WIPACrepo/wipac-telemetry?include_prereleases)](https://github.com/WIPACrepo/wipac-telemetry/) [![PyPI - License](https://img.shields.io/pypi/l/wipac-telemetry)](https://github.com/WIPACrepo/wipac-telemetry/blob/main/LICENSE) [![Lines of code](https://img.shields.io/tokei/lines/github/WIPACrepo/wipac-telemetry)](https://github.com/WIPACrepo/wipac-telemetry/) [![GitHub issues](https://img.shields.io/github/issues/WIPACrepo/wipac-telemetry)](https://github.com/WIPACrepo/wipac-telemetry/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/WIPACrepo/wipac-telemetry)](https://github.com/WIPACrepo/wipac-telemetry/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# wipac-telemetry
WIPAC Telemetry: Monitoring/Tracing Applications, Supporting Infrastructures, and Services

## Tracing Tools

### Configuration
Most of the major functionality is configurable via environment variables. **_Traces are not exported by default._**

#### Environment Variables
Name                          |  Type/Options         | Description                                | Null Case          | Example & Notes
----------------------------- | --------------------- | ------------------------------------------ | ------------------ | --------------- |
`OTEL_EXPORTER_OTLP_ENDPOINT` | string                | address of collector service               | no traces exported | `https://my.url.aq/traces/go/here`
`WIPACTEL_EXPORT_STDOUT`      | `True` or `False`     | whether to print the traces                | no traces printed  |
`WIPACTEL_LOGGING_LEVEL`      | `debug`, `info`, etc. | minimum logging level for WIPACTEL actions | `warning` (or root logger's level if that's higher)
`WIPACTEL_SERVICE_NAME_PREFIX`| string                | prefix for the tracing service's name      | `""`               | `mou` (results in a service called "mou/server" instead of just "server")

## Running with Local Collector Service UI (Jaegar)
1. `cd examples/telemetry-server/jaeger-production && ./start-jaeger-production.sh`
1. Open new terminal:
1. `export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces`
1. Run script(s) and/or module(s)
1. Go to <http://localhost:16686/>
