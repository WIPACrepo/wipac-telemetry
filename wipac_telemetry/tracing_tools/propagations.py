"""Tools for cross-service propagation."""


from opentelemetry import propagate  # type: ignore[import]

inject = propagate.inject  # Inject the Span Context for HTTP tracing propagation
