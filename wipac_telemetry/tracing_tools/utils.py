"""Common tools for interacting with the OpenTelemetry Tracing API."""


import copy
import inspect
import logging
from collections.abc import Sequence
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from opentelemetry import trace
from opentelemetry.util import types

# Constants ############################################################################

LOGGER = logging.getLogger("wipac-telemetry")


# Types ################################################################################

Args = Tuple[Any, ...]
Kwargs = Dict[str, Any]


# Aliases ##############################################################################

# aliases for easy importing
Span = trace.Span
OptSpan = Optional[Span]  # alias used for Span-argument injection
Link = trace.Link
get_current_span = trace.get_current_span
SpanKind = trace.SpanKind


# Classes/Functions ####################################################################


class FunctionInspection:
    """A wrapper around a function and its introspection functionalities."""

    def __init__(self, func: Callable[..., Any], args: Args, kwargs: Kwargs):
        bound_args = inspect.signature(func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        self.param_args = dict(bound_args.arguments)

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def rget(
        self, var_name: str, typ: Union[None, type, Tuple[type, ...]] = None
    ) -> Any:
        """Retrieve the instance at `var_name` from signature-parameter args.

        Optionally, check if the value is of type(s), `type`.

        Searches:
            - non-callable objects
            - supports nested/chained attributes (including `self.*` attributes)
            - supports literal dict-member access, both dot and bracket-quote syntax

        Examples:
            signature -> (self, foo)
            variable names -> self.green, foo, foo.bar.baz, foo.bam['boom'] or foo.bam.boom

        Raises:
            AttributeError -- if var_name is not found
            TypeError -- if the instance is found, but isn't of the type(s) indicated
        """
        LOGGER.debug(f"rget: {var_name}")
        # very any dict-access, and convert bracket-quote syntax to dot syntax
        if "[" in var_name:
            for i, char in enumerate(var_name):
                try:
                    if char == "[" and var_name[i + 1] not in ['"', "'"]:
                        raise AttributeError(
                            f"'{var_name}': cannot contain variable dict-keys"
                        )
                except IndexError:
                    raise AttributeError(f"'{var_name}': malformed dict syntax")
            var_name = var_name.replace("[", ".")
            for char in ["'", '"', "]"]:
                var_name = var_name.replace(char, "")

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
            LOGGER.debug(f"rget: {var_name} -> obj={obj}({type(attr)}) attr={attr}")
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


def convert_to_attributes(
    raw: Union[Dict[str, Any], types.Attributes]
) -> types.Attributes:
    """Convert dict to mapping of attributes (deep copy values).

    Bad values are disregarded.
    """
    if not raw:
        return {}

    skips = []
    legal_types = (str, bool, int, float)
    for attr in list(raw):
        if isinstance(raw[attr], legal_types):
            continue
        # check all members are of same (legal) type
        if isinstance(raw[attr], Sequence):
            member_types = list(set(type(m) for m in raw[attr]))  # type: ignore[union-attr]
            if len(member_types) == 1 and member_types[0] in legal_types:
                continue
        # illegal type
        skips.append(attr)

    return {k: copy.deepcopy(v) for k, v in raw.items() if k not in skips}


def wrangle_attributes(
    attributes: types.Attributes,
    func_inspect: FunctionInspection,
    all_args: bool,
    these: Optional[List[str]],
) -> types.Attributes:
    """Figure what attributes to use from the list and/or function args."""
    raw: Dict[str, Any] = {}

    if these:
        raw.update({a: func_inspect.rget(a) for a in these})

    if all_args:
        raw.update(func_inspect.param_args)

    if attributes:
        raw.update(attributes)

    return convert_to_attributes(raw)
