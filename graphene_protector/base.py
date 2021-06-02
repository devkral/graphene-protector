from graphql.backend.core import GraphQLCoreBackend
from graphql.language.ast import (
    FragmentDefinition,
    FragmentSpread,
    OperationDefinition,
)
import re

from dataclasses import dataclass, fields, replace
from typing import Union


# Adapted from this response in Stackoverflow
# http://stackoverflow.com/a/19053800/1072990
def to_camel_case(snake_str):
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + "".join(
        x.capitalize() if x else "_" for x in components[1:]
    )


# From this response in Stackoverflow
# http://stackoverflow.com/a/1176023/1072990
def to_snake_case(name):
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


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
DEFAULT_LIMITS = Limits(depth=20, selections=None, complexity=100)


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
    auto_snakecase=False,
    level=0,
):
    # level 0: starts on query level. Every query is level 1
    selections = 0
    max_depth = level
    if limits.depth and max_depth > limits.depth:
        raise DepthLimitReached("Query is too deep")
    for field_orig in selection_set.selections:
        fieldname = field_orig.name.value
        if auto_snakecase and not hasattr(schema, fieldname):
            fieldname = to_snake_case(fieldname)
        if isinstance(field_orig, FragmentSpread):
            field = fragments.get(field_orig.name.value)
        else:
            field = field_orig
        if field.selection_set:
            schema_field = getattr(schema, fieldname)
            sub_limits = limits_for_field(schema_field, limits)
            new_depth, local_selections = check_resource_usage(
                schema_field.type,
                field.selection_set,
                fragments,
                sub_limits,
                auto_snakecase=auto_snakecase,
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
            operation_type = definition.operation

            check_resource_usage(
                getattr(schema, f"_{operation_type}"),
                definition.selection_set,
                fragments,
                self.get_default_limits(),
                auto_snakecase=getattr(schema, "auto_camelcase", False),
            )

        return document

    def get_default_limits(self):
        return merge_limits(
            DEFAULT_LIMITS,
            self.default_limits,
        )
