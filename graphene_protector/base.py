from graphql.backend.core import GraphQLCoreBackend
from graphql.language.ast import (
    FragmentDefinition,
    FragmentSpread,
    OperationDefinition,
)


from dataclasses import dataclass, InitVar, fields
from typing import Union


class MISSING:
    pass


@dataclass
class Limits:
    obj: InitVar = None
    depth: Union[int, None, MISSING] = MISSING
    selections: Union[int, None, MISSING] = MISSING
    complexity: Union[int, None, MISSING] = MISSING

    def __post_init__(self, obj):
        # TODO: decorate base of obj with _graphene_protector_limits
        pass


_missing_limits = Limits()


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


def check_resource_usage(
    selection_set,
    fragments,
    depth_limit,
    selections_limit,
    complexity_limit,
    level=1,
):
    selections = 1
    max_depth = level
    if depth_limit and max_depth > depth_limit:
        raise DepthLimitReached("Query is too deep")
    for field in selection_set.selections:
        if isinstance(field, FragmentSpread):
            field = fragments.get(field.name.value)
        if field.selection_set:
            new_depth, local_selections = check_resource_usage(
                field.selection_set,
                fragments,
                depth_limit,
                selections_limit,
                complexity_limit,
                level=level + 1,
            )
            selections += local_selections
            if selections_limit and selections > selections_limit:
                raise SelectionsLimitReached("Query selects too much")
            if (
                complexity_limit
                and (new_depth - level) * local_selections > complexity_limit
            ):
                ComplexityLimitReached("Query is too complex")
            if new_depth > max_depth:
                max_depth = new_depth
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
                definition.selection_set,
                fragments,
                self.depth_limit,
                self.selections_limit,
                self.complexity_limit,
            )

        return document

    def _current_operation_merged_limits(self, schema, definition):
        # operation type is 'query' or 'mutation'
        operation_type = definition.operation

        # query or mutation name
        operation_name = definition.selection_set.selections[0].name.value

        # operator (query or mutation) object defined in the schema
        operator = getattr(schema, f"_{operation_type}")

        # retrieve optional limitation attributes defined for the current
        # operation
        operation_limits = getattr(
            operator, "_graphene_protector_limits", {}
        ).get(operation_name, _missing_limits)
        _limits = {}
        for field in fields(operation_limits):
            value = getattr(operation_limits, field.name)
            if not isinstance(value, MISSING):
                return value
            value = getattr(self.default_limits, field.name)
            if not isinstance(value, MISSING):
                return value
            return self._limits_for_missing(field.name)

        return _limits

    def _limits_for_missing(self, name):
        if name == "depth":
            return 20
        elif name == "selections":
            return None
        elif name == "complexity":
            return 100
