"""Common tools for interacting with the OpenTelemetry Tracing API."""


import copy
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

from opentelemetry.trace import Span
from opentelemetry.util import types

from .config import LOGGER

__all__ = ["LOGGER"]

LEGAL_ATTR_BASE_TYPES = (str, bool, int, float)


# Types ################################################################################

Args = Tuple[Any, ...]
Kwargs = Dict[str, Any]


# Classes/Functions ####################################################################


class FunctionInspector:
    """A wrapper around a function and its introspection functionalities."""

    def __init__(self, func: Callable[..., Any], args: Args, kwargs: Kwargs):
        bound_args = inspect.signature(func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        self.param_args = dict(bound_args.arguments)

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def resolve_attr(
        self, var_name: str, typ: Union[None, type, Tuple[type, ...]] = None
    ) -> Any:
        """Retrieve the instance at `var_name` from signature-parameter args.

        Optionally, check if the value is of type(s), `type`.

        Searches:
            - non-callable objects
            - supports nested/chained attributes (including `self.*` attributes)
            - supports literal dict-member access in dot syntax,
                + ex: for bam['boom'] use bam.boom

        Examples:
            signature -> (self, foo)
            variable names -> self.green, foo, foo.bar.baz, foo.bam.boom

        Raises:
            AttributeError -- if var_name is not found
            TypeError -- if the instance is found, but isn't of the type(s) indicated
        """
        LOGGER.debug(f"rget({var_name}, {typ})")

        def dot_left(string: str) -> str:
            return string.split(".", maxsplit=1)[0]

        def dot_right(string: str) -> str:
            try:
                return string.split(".", maxsplit=1)[1]
            except IndexError:
                return ""

        def _get_attr_or_value(obj: Any, attr: str) -> Any:
            if isinstance(obj, dict):
                return obj.get(attr, None)
            else:
                return getattr(obj, attr)

        def _rget(obj: Any, attr: str) -> Any:
            if not attr:
                return obj
            elif "." in attr:
                left_attr = _get_attr_or_value(obj, dot_left(attr))
                return _rget(left_attr, dot_right(attr))
            else:
                return _get_attr_or_value(obj, attr)

        try:
            obj = _rget(self.param_args[dot_left(var_name)], dot_right(var_name))
        except AttributeError as e:
            raise AttributeError(  # pylint: disable=W0707
                f"'{var_name}': {e} "
                f"(present parameter arguments: {', '.join(self.param_args.keys())})"
            )
        except KeyError:
            raise AttributeError(  # pylint: disable=W0707
                f"'{var_name}': function parameters have no argument '{dot_left(var_name)}' "
                f"(present parameter arguments: {', '.join(self.param_args.keys())})"
            )

        if typ and not isinstance(obj, typ):
            raise TypeError(f"Instance '{var_name}' is not {typ}")
        return obj

    def wrangle_otel_attributes(
        self,
        all_args: bool,
        these: Optional[List[str]],
        other_attributes: types.Attributes,
    ) -> types.Attributes:
        """Figure what attributes to use from the list and/or function args."""
        raw: Dict[str, Any] = {}

        if these:
            raw.update({a: self.resolve_attr(a) for a in these})

        if all_args:
            raw.update(self.param_args)

        if other_attributes:
            raw.update(other_attributes)

        return convert_to_attributes(raw)

    def get_span(self, span_var_name: str) -> Span:
        """Get the Span instance at `span_var_name`."""
        return cast(Span, self.resolve_attr(span_var_name))


def convert_to_attributes(
    raw: Union[Dict[str, Any], types.Attributes]
) -> types.Attributes:
    """Convert dict to mapping of attributes (deep copy values).

    Values that aren't str/bool/int/float (or homogeneous
    "Optional" tuples/lists of these) are swapped for
    their `repr()` strings, wholesale.

    From OTEL API:
        AttributeValue = Union[
            str,
            bool,
            int,
            float,
            Sequence[Optional[str]],
            Sequence[Optional[bool]],
            Sequence[Optional[int]],
            Sequence[Optional[float]],
        ]

    Note: Types of sequences other than tuple and list are
    treated as "other types", despite the OTEL API definition.
    This is to safeguard against, tricky sequences like `bytes`,
    custom instances, etc.
    """
    if not raw:
        return {}

    out = {}

    for attr in list(raw):
        # check if simple, single type
        if isinstance(raw[attr], LEGAL_ATTR_BASE_TYPES):
            out[attr] = copy.deepcopy(raw[attr])

        # is this a tuple/list?
        elif isinstance(raw[attr], (tuple, list)):
            # get all types (but ignore `None`s b/c they're always allowed)
            member_types = list(set(type(m) for m in raw[attr] if m is not None))  # type: ignore[union-attr]
            # if every member is same (legal) type, copy it all
            if len(member_types) == 1 and member_types[0] in LEGAL_ATTR_BASE_TYPES:
                out[attr] = copy.deepcopy(raw[attr])
            # otherwise: retain list, but as reprs (strs)
            else:
                out[attr] = [repr(v) for v in raw[attr]]  # type: ignore[union-attr]

        # other types -> get `repr()`
        else:
            out[attr] = repr(raw[attr])

    return out
