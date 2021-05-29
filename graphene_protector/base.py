from graphql.backend.core import GraphQLCoreBackend
from graphql.language.ast import (
    FragmentDefinition,
    FragmentSpread,
    OperationDefinition,
)


from dataclasses import dataclass, fields, replace
from typing import Union


class MISSING:
    pass


@dataclass
class Limits:
    depth: Union[int, None, MISSING] = MISSING
    selections: Union[int, None, MISSING] = MISSING
    complexity: Union[int, None, MISSING] = MISSING

    def __call__(self, field):
        setattr(field, "_graphene_protector_limits", self)
        return field


_missing_limits = Limits()
_default_limits = Limits(depth=20, selections=None, complexity=100)


class ResourceLimitReached(Exception):
    pass


class DepthLimitReached(ResourceLimitReached):
    pass


class SelectionsLimitReached(ResourceLimitReached):
    pass


class ComplexityLimitReached(ResourceLimitReached):
    pass


# stolen from https://github.com/manesioz/secure-graphene/blob/master/secure_graphene/depth.py  # noqa E501
def get_fragments(definitions):
    return {
        definition.name.value: definition
        for definition in definitions
        if isinstance(definition, FragmentDefinition)
    }


def merge_limits(old_limits, new_limits):
    _limits = {}
    for field in fields(new_limits):
        value = getattr(new_limits, field.name)
        if value != MISSING:
            _limits[field.name] = value
    return replace(old_limits, **_limits)


def limits_for_field(field, old_limits):
    # retrieve optional limitation attributes defined for the current
    # operation
    effective_limits = getattr(
        field,
        "_graphene_protector_limits",
        _missing_limits,
    )
    return merge_limits(old_limits, effective_limits)


def check_resource_usage(
    selection_set,
    fragments,
    limits,
    level=0,
):
    # level 0: starts on query level. Every query is level 1
    selections = 0
    max_depth = level
    if limits.depth and max_depth > limits.depth:
        raise DepthLimitReached("Query is too deep")
    for field in selection_set.selections:
        # must be before fragments.get
        newlimits = limits_for_field(field, limits)
        if isinstance(field, FragmentSpread):
            field = fragments.get(field.name.value)
        if field.selection_set:
            new_depth, local_selections = check_resource_usage(
                field.selection_set,
                fragments,
                newlimits,
                level=level + 1,
            )
            # called per query, selection
            if (
                limits.complexity
                and (new_depth - level) * local_selections > limits.complexity
            ):
                ComplexityLimitReached("Query is too complex")
            # +1 because { ... } is also a selection/field
            selections += local_selections + 1
            if new_depth > max_depth:
                max_depth = new_depth
        else:
            selections += 1

        if limits.selections and selections > limits.selections:
            raise SelectionsLimitReached("Query selects too much")
    return max_depth, selections


class ProtectorBackend(GraphQLCoreBackend):
    default_limits = None

    def __init__(self, *args, limits=Limits(), **kwargs):
        super().__init__(*args, **kwargs)
        self.default_limits = limits

    def document_from_string(self, schema, document_string):
        document = super().document_from_string(schema, document_string)
        ast = document.document_ast
        # fragments are like a dictionary of views
        fragments = get_fragments(ast.definitions)
        for definition in ast.definitions:
            # only queries and mutations
            if not isinstance(definition, OperationDefinition):
                continue

            check_resource_usage(
                definition.selection_set, fragments, self.get_default_limits()
            )

        return document

    def get_default_limits(self):
        return merge_limits(
            _default_limits,
            self.default_limits,
        )
