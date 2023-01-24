import sys
from dataclasses import dataclass
from typing import Union
from graphql.error import GraphQLError


class MISSING:
    """custom MISSING sentinel for merge logic"""


_deco_options = {}
if sys.version_info >= (3, 10):
    _deco_options["slots"] = True

if sys.version_info >= (3, 11):
    _deco_options["weakref_slot"] = True


@dataclass(frozen=True, **_deco_options)
class Limits:
    depth: Union[int, None, MISSING] = MISSING
    selections: Union[int, None, MISSING] = MISSING
    complexity: Union[int, None, MISSING] = MISSING

    def __call__(self, field):
        setattr(field, "_graphene_protector_limits", self)
        return field


MISSING_LIMITS = Limits()
DEFAULT_LIMITS = Limits(depth=20, selections=None, complexity=100)


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


# the worst problem for calculations is edges/node as it increases the
# complexity and depth count by 2
# the other parts does not affect the calculations by these magnitudes
default_path_ignore_pattern = "edges/node$"
