__all__ = [
    "MISSING",
    "Limits",
    "UsagesResult",
    "DEFAULT_LIMITS",
    "MISSING_LIMITS",
    "EarlyStop",
    "ResourceLimitReached",
    "DepthLimitReached",
    "SelectionsLimitReached",
    "ComplexityLimitReached",
    "GasLimitReached",
    "default_path_ignore_pattern",
]

import copy
import sys
from dataclasses import dataclass
from typing import Set, Union

from graphql.error import GraphQLError

_empty_set = frozenset()


class MISSING:
    """
    custom MISSING sentinel as dataclass MISSING has different logic and
    cannot be used as Sentinel like here
    """


_deco_options = {}
if sys.version_info >= (3, 10):
    _deco_options["kw_only"] = True
    _deco_options["slots"] = True

if sys.version_info >= (3, 11):
    _deco_options["weakref_slot"] = True


@dataclass(frozen=True, **_deco_options)
class Limits:
    depth: Union[int, None, MISSING] = MISSING
    selections: Union[int, None, MISSING] = MISSING
    complexity: Union[int, None, MISSING] = MISSING
    gas: Union[int, None, MISSING] = MISSING
    # only for sublimits not for main Limit instance
    # passthrough for not missing limits
    passthrough: Set[str] = _empty_set

    def __call__(self, field):
        # ensure every decoration has an own id
        setattr(field, "_graphene_protector_limits", copy.copy(self))
        return field


@dataclass(**_deco_options)
class UsagesResult:
    max_level_depth: int = 0
    max_level_complexity: int = 0
    selections: int = 0
    gas_used: int = 0


MISSING_LIMITS = Limits()
DEFAULT_LIMITS = Limits(depth=20, selections=None, complexity=100, gas=None)


class EarlyStop(Exception):
    pass


class ResourceLimitReached(GraphQLError):
    pass


class DepthLimitReached(ResourceLimitReached):
    pass


class SelectionsLimitReached(ResourceLimitReached):
    pass


class ComplexityLimitReached(ResourceLimitReached):
    pass


class GasLimitReached(ResourceLimitReached):
    pass


# the worst problem for calculations is edges/node as it increases the
# complexity and depth count by 2
# the other parts does not affect the calculations by these magnitudes
default_path_ignore_pattern = "edges/node$"
