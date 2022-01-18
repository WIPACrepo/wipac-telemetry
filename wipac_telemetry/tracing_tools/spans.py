"""Tools for working with spans."""


import asyncio
import inspect
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, List, Optional

try:
    from typing import Final, TypedDict
except ImportError:
    from typing_extensions import Final, TypedDict  # type: ignore[misc]

from opentelemetry.propagate import extract
from opentelemetry.trace import Span, SpanKind, get_current_span, get_tracer, use_span
from opentelemetry.util import types

from .propagations import extract_links_carrier
from .utils import LOGGER, Args, FunctionInspector, Kwargs

########################################################################################


class CarrierRelation(Enum):
    """Enum for indicating what span relation is intended for the carrier."""

    SPAN_CHILD = auto()  # a hierarchical/vertical/parent-child relation
    LINK = auto()  # a lateral/horizontal relation


class SpanBehavior(Enum):
    """Enum for indicating type of span behavior is wanted."""

    END_ON_EXIT = auto()
    DONT_END = auto()
    ONLY_END_ON_EXCEPTION = auto()


class InvalidSpanBehavior(ValueError):
    """Raise when an invalid SpanBehavior value is attempted."""


class SpanNamer:
    """Build a name for the span from various sources.

    Those set to `None` are ignored.

    Build Order Pattern: "[<function_name>:][<literal_name>:][<use_this_arg>]"
    Examples:
        - `SpanNamer(literal_name="MyCustomName", use_function_name=True, use_this_arg="self.request.method")`
            "MyClass.my_method:MyCustomName:POST"
        - `SpanNamer(literal_name="MyCustomName", use_function_name=False)`
            "MyCustomName:POST"
        - `SpanNamer(use_function_name=True)`
            "MyClass.my_method"
        - `SpanNamer(use_function_name=False)`
            "MyClass.my_method" (there has to be a span name!)

    Arguments:
        literal_name: a literal name that will be used verbatim
        use_this_arg: the name of a function-argument (or sub-argument) that will be used
        use_function_name: whether to use the wrapped function's name
    """

    def __init__(
        self,
        literal_name: Optional[str] = None,
        use_this_arg: Optional[str] = None,
        use_function_name: bool = True,
    ) -> None:
        self.literal_name = literal_name
        self.use_this_arg = use_this_arg
        self.use_function_name = use_function_name

        # if everything is essentially blank, then fallback to using the function's name
        if not any([self.literal_name, self.use_this_arg, self.use_function_name]):
            self.use_function_name = True

    def build_name(self, inspector: FunctionInspector) -> str:
        """Build and return the span name."""
        builder = []

        if self.use_function_name:
            builder.append(inspector.func.__qualname__)  # ex: MyClass.my_method
        if self.literal_name:
            builder.append(self.literal_name)
        if self.use_this_arg:
            builder.append(str(inspector.resolve_attr(self.use_this_arg)))

        return ":".join(builder)


########################################################################################


class _OTELAttributeSettings(TypedDict):
    attributes: types.Attributes
    all_args: bool
    these: List[str]


########################################################################################


class _SpanConductor:
    """Conduct necessary processes for Span-availability."""

    def __init__(
        self,
        otel_attrs_settings: _OTELAttributeSettings,
        behavior: SpanBehavior,
        autoevent_reason: str,
    ):
        self.otel_attrs_settings = otel_attrs_settings
        self.behavior = behavior
        self._autoevent_reason_value: Final = autoevent_reason

    def get_span(self, inspector: FunctionInspector) -> Span:
        """Get a span, configure according to sub-class."""
        raise NotImplementedError()

    def auto_event_attrs(self, addl_links: types.Attributes) -> types.Attributes:
        """Get the event attributes for auto-eventing a span."""
        return {
            "spanned_reason": self._autoevent_reason_value,
            "span_behavior": str(self.behavior),
            "added_attributes": list(addl_links.keys()) if addl_links else [],
        }


class _NewSpanConductor(_SpanConductor):
    """Conduct necessary processes for making a new Span available."""

    def __init__(
        self,
        otel_attrs_settings: _OTELAttributeSettings,
        behavior: SpanBehavior,
        span_namer: SpanNamer,
        kind: SpanKind,
        carrier: str,
        carrier_relation: CarrierRelation,
    ):
        super().__init__(otel_attrs_settings, behavior, "premiere")
        self.span_namer = span_namer
        self.kind = kind
        self.carrier = carrier
        self.carrier_relation = carrier_relation

    def get_span(self, inspector: FunctionInspector) -> Span:
        """Set up, start, and return a new span instance."""
        span_name = self.span_namer.build_name(inspector)
        tracer_name = inspect.getfile(inspector.func)  # Ex: /path/to/file.py

        if self.carrier and self.carrier_relation == CarrierRelation.SPAN_CHILD:
            context = extract(inspector.resolve_attr(self.carrier))
        else:
            context = None  # `None` will default to current context

        links = []
        if self.carrier and self.carrier_relation == CarrierRelation.LINK:
            links = extract_links_carrier(inspector.resolve_attr(self.carrier))

        attrs = inspector.wrangle_otel_attributes(
            self.otel_attrs_settings["all_args"],
            self.otel_attrs_settings["these"],
            self.otel_attrs_settings["attributes"],
        )

        tracer = get_tracer(tracer_name)
        span = tracer.start_span(
            span_name, context=context, kind=self.kind, attributes=attrs, links=links
        )
        span.add_event(span_name, self.auto_event_attrs(attrs))

        LOGGER.info(
            f"Started span `{span_name}` for tracer `{tracer_name}` with: "
            f"attributes={list(attrs.keys()) if attrs else []}, "
            f"links={[k.context for k in links] if links else None}"
        )

        return span


class _ReuseSpanConductor(_SpanConductor):
    """Conduct necessary processes for reusing an existing Span."""

    def __init__(
        self,
        otel_attrs_settings: _OTELAttributeSettings,
        behavior: SpanBehavior,
        span_var_name: Optional[str],
    ):
        super().__init__(otel_attrs_settings, behavior, "respanned")
        self.span_var_name = span_var_name

    def get_span(self, inspector: FunctionInspector) -> Span:
        """Find, supplement, and return an exiting span instance."""
        if self.span_var_name:
            span = inspector.get_span(self.span_var_name)
        else:
            span = get_current_span()

        attrs = inspector.wrangle_otel_attributes(
            self.otel_attrs_settings["all_args"],
            self.otel_attrs_settings["these"],
            self.otel_attrs_settings["attributes"],
        )
        if attrs:  # this may override existing attributes
            for key, value in attrs.items():
                span.set_attribute(key, value)

        span.add_event(inspector.func.__qualname__, self.auto_event_attrs(attrs))

        if self.behavior == SpanBehavior.END_ON_EXIT:
            if span == get_current_span():
                raise InvalidSpanBehavior(
                    'Attempting to re-span the "current" span '
                    "with `behavior=SpanBehavior.END_ON_EXIT` "
                    "(callee should not explicitly end caller's span)."
                )

        LOGGER.info(
            f"Re-using span `{span.name}` "  # type: ignore[attr-defined]
            f"(from '{self.span_var_name if self.span_var_name else 'current-span'}') "
            f"with: additional attributes={list(attrs.keys()) if attrs else []}"
        )

        return span


########################################################################################


def _spanned(scond: _SpanConductor) -> Callable[..., Any]:
    """Handle decorating a function with either a new span or a reused span."""

    def inner_function(func: Callable[..., Any]) -> Callable[..., Any]:
        def setup(args: Args, kwargs: Kwargs) -> Span:
            if not isinstance(scond, (_NewSpanConductor, _ReuseSpanConductor)):
                raise Exception(f"Undefined SpanConductor type: {scond}.")
            else:
                return scond.get_span(FunctionInspector(func, args, kwargs))

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Function")
            span = setup(args, kwargs)
            is_iterator_class_next_method = span.name.endswith(".__next__")  # type: ignore[attr-defined]
            reraise_stopiteration_outside_contextmanager = False

            # CASE 1 ----------------------------------------------------------
            if scond.behavior == SpanBehavior.ONLY_END_ON_EXCEPTION:
                try:
                    with use_span(span, end_on_exit=False):
                        try:
                            return func(*args, **kwargs)
                        except StopIteration:
                            # intercept and temporarily suppress StopIteration
                            if not is_iterator_class_next_method:
                                raise
                            reraise_stopiteration_outside_contextmanager = True
                except:  # noqa: E722 # pylint: disable=bare-except
                    span.end()
                    raise
                if reraise_stopiteration_outside_contextmanager:
                    raise StopIteration
                raise RuntimeError("Malformed SpanBehavior Handling")
            # CASES 2 & 3 -----------------------------------------------------
            elif scond.behavior in (SpanBehavior.END_ON_EXIT, SpanBehavior.DONT_END):
                end_on_exit = bool(scond.behavior == SpanBehavior.END_ON_EXIT)
                with use_span(span, end_on_exit=end_on_exit):
                    try:
                        return func(*args, **kwargs)
                    except StopIteration:
                        # intercept and temporarily suppress StopIteration
                        if not is_iterator_class_next_method:
                            raise
                        reraise_stopiteration_outside_contextmanager = True
                if reraise_stopiteration_outside_contextmanager:
                    raise StopIteration
                raise RuntimeError("Malformed SpanBehavior Handling")
            # ELSE ------------------------------------------------------------
            else:
                raise InvalidSpanBehavior(scond.behavior)

        @wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Generator Function")
            span = setup(args, kwargs)

            # CASE 1 ----------------------------------------------------------
            if scond.behavior == SpanBehavior.ONLY_END_ON_EXCEPTION:
                try:
                    with use_span(span, end_on_exit=False):
                        for val in func(*args, **kwargs):
                            yield val
                except:  # noqa: E722 # pylint: disable=bare-except
                    span.end()
                    raise
            # CASES 2 & 3 -----------------------------------------------------
            elif scond.behavior in (SpanBehavior.END_ON_EXIT, SpanBehavior.DONT_END):
                end_on_exit = bool(scond.behavior == SpanBehavior.END_ON_EXIT)
                with use_span(span, end_on_exit=end_on_exit):
                    for val in func(*args, **kwargs):
                        yield val
            # ELSE ------------------------------------------------------------
            else:
                raise InvalidSpanBehavior(scond.behavior)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            LOGGER.debug("Spanned Async Function")
            span = setup(args, kwargs)
            is_iterator_class_anext_method = span.name.endswith(".__anext__")  # type: ignore[attr-defined]
            reraise_stopasynciteration_outside_contextmanager = False

            # CASE 1 ----------------------------------------------------------
            if scond.behavior == SpanBehavior.ONLY_END_ON_EXCEPTION:
                try:
                    with use_span(span, end_on_exit=False):
                        try:
                            return await func(*args, **kwargs)
                        except StopAsyncIteration:
                            # intercept and temporarily suppress StopAsyncIteration
                            if not is_iterator_class_anext_method:
                                raise
                            reraise_stopasynciteration_outside_contextmanager = True
                except:  # noqa: E722 # pylint: disable=bare-except
                    span.end()
                    raise
                if reraise_stopasynciteration_outside_contextmanager:
                    raise StopAsyncIteration
                raise RuntimeError("Malformed SpanBehavior Handling")
            # CASES 2 & 3 -----------------------------------------------------
            elif scond.behavior in (SpanBehavior.END_ON_EXIT, SpanBehavior.DONT_END):
                end_on_exit = bool(scond.behavior == SpanBehavior.END_ON_EXIT)
                with use_span(span, end_on_exit=end_on_exit):
                    try:
                        return await func(*args, **kwargs)
                    except StopAsyncIteration:
                        # intercept and temporarily suppress StopAsyncIteration
                        if not is_iterator_class_anext_method:
                            raise
                        reraise_stopasynciteration_outside_contextmanager = True
                if reraise_stopasynciteration_outside_contextmanager:
                    raise StopAsyncIteration
                raise RuntimeError("Malformed SpanBehavior Handling")
            # ELSE ------------------------------------------------------------
            else:
                raise InvalidSpanBehavior(scond.behavior)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            if inspect.isgeneratorfunction(func):
                return gen_wrapper
            else:
                return wrapper

    return inner_function


########################################################################################


def spanned(
    span_namer: Optional[SpanNamer] = None,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
    behavior: SpanBehavior = SpanBehavior.END_ON_EXIT,
    kind: SpanKind = SpanKind.INTERNAL,
    carrier: Optional[str] = None,
    carrier_relation: CarrierRelation = CarrierRelation.SPAN_CHILD,
) -> Callable[..., Any]:
    """Decorate to trace a function in a new span.

    Also, record an event with the function's name and the names of the
    attributes added.

    Keyword Arguments:
        span_namer -- `SpanNamer` instance for naming the span
                    - if not provided, use function's qualified name
                    - see `SpanNamer` for naming options
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes
        behavior -- indicate what type of span behavior is wanted:
                    - `SpanBehavior.END_ON_EXIT`
                        + start span as the current span (accessible via `get_current_span()`)
                        + automatically end span (send traces) when function returns
                        + default value
                    - `SpanBehavior.DONT_END`
                        + start span as the current span (accessible via `get_current_span()`)
                        + requires a call to `span.end()` to send traces
                            - (or subsequent `@respanned()` with necessary `behavior` setting)
                        + can be persisted between independent functions
                        + use this when re-use is needed and an exception IS expected
                        + traces are sent if the function call is wrapped in a try-except
                    - `SpanBehavior.ONLY_END_ON_EXCEPTION`
                        + similar to `SpanBehavior.DONT_END` but auto-ends when an exception is raised
                        + use this when re-use is needed and an exception is NOT expected
        kind -- a `SpanKind` enum value
                - `SpanKind.INTERNAL` - (default) normal, in-application spans
                - `SpanKind.CLIENT` - the spanned function sends cross-service requests
                - `SpanKind.SERVER` - the spanned function receives cross-service requests (and may reply)
                - `SpanKind.PRODUCER` - the spanned function sends cross-service messages
                - `SpanKind.CONSUMER` - the spanned function receives cross-service messages
        carrier -- the name of the variable containing the carrier dict - useful for cross-process/service tracing
        carrier_relation -- a `CarrierRelation` enum value, used alongside `carrier`
                            - `CarrierRelation.SPAN_CHILD` - (default) for parent-child span relations
                            - `CarrierRelation.LINK` - for lateral/horizontal span relations

    Raises a `ValueError` when attempting to self-link the independent/injected span
    Raises a `InvalidSpanBehavior` when an invalid `behavior` value is attempted
    """
    if not these:
        these = []
    if not span_namer:
        span_namer = SpanNamer()
    if not carrier:
        carrier = ""

    return _spanned(
        _NewSpanConductor(
            {"attributes": attributes, "all_args": all_args, "these": these},
            behavior,
            span_namer,
            kind,
            carrier,
            carrier_relation,
        )
    )


def respanned(
    span_var_name: Optional[str],
    behavior: SpanBehavior,
    attributes: types.Attributes = None,
    all_args: bool = False,
    these: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Decorate to trace a function with an existing span.

    Also, record an event with the function's name and the names of the
    attributes added.

    Arguments:
        span_var_name -- name of Span instance variable; if None (or ""), the current-span is used
        behavior -- indicate what type of span behavior is wanted:
                    - `SpanBehavior.END_ON_EXIT`
                        + start span as the current span (accessible via `get_current_span()`)
                        + automatically end span (send traces) when function returns
                        + default value
                    - `SpanBehavior.DONT_END`
                        + start span as the current span (accessible via `get_current_span()`)
                        + requires a call to `span.end()` to send traces
                            - (or subsequent `@respanned()` with necessary `behavior` setting)
                        + can be persisted between independent functions
                        + use this when re-use is needed and an exception IS expected
                        + (traces are sent if the function call is wrapped in a try-except)
                    - `SpanBehavior.ONLY_END_ON_EXCEPTION`
                        + similar to `SpanBehavior.DONT_END` but auto-ends when an exception is raised
                        + use this when re-use is needed and an exception is NOT expected

    Keyword Arguments:
        attributes -- a dict of attributes to add to span
        all_args -- whether to auto-add all the function-arguments as attributes
        these -- a whitelist of function-arguments and/or `self.*`-variables to add as attributes

    Raises an `InvalidSpanBehavior` when an invalid `behavior` value is attempted
    """
    if not these:
        these = []

    return _spanned(
        _ReuseSpanConductor(
            {"attributes": attributes, "all_args": all_args, "these": these},
            behavior,
            span_var_name,
        )
    )
