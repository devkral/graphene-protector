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
    schema,
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
    for field_orig in selection_set.selections:
        if isinstance(field_orig, FragmentSpread):
            field = fragments.get(field_orig.name.value)
        else:
            field = field_orig
        if field.selection_set:
            subschema = getattr(schema, field_orig.name.value).type
            sub_limits = limits_for_field(
                getattr(schema, field_orig.name.value), limits
            )
            new_depth, local_selections = check_resource_usage(
                subschema,
                field.selection_set,
                fragments,
                sub_limits,
                level=level + 1,
            )
            # called per query, selection
            if (
                sub_limits.complexity
                and (new_depth - level) * local_selections
                > sub_limits.complexity
            ):
                raise ComplexityLimitReached("Query is too complex")
            # ignore selection_set fields because we have depth for that
            selections += local_selections
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
                schema._query,
                definition.selection_set,
                fragments,
                self.get_default_limits(),
            )

        return document

    def get_default_limits(self):
        return merge_limits(
            _default_limits,
            self.default_limits,
        )
