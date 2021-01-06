from graphql.backend.core import GraphQLCoreBackend
from graphql.language.ast import (
    FragmentDefinition,
    FragmentSpread,
    OperationDefinition
)


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
    selection_set, fragments, depth_limit, selections_limit, complexity_limit,
    level=1
):
    selections = 1
    max_depth = level
    if depth_limit and max_depth > depth_limit:
        raise DepthLimitReached('Query is too deep')
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
                level=level + 1
            )
            selections += local_selections
            if selections_limit and selections > selections_limit:
                raise SelectionsLimitReached(
                    'Query selects too much'
                )
            if (
                complexity_limit and
                (new_depth-level) * local_selections > complexity_limit
            ):
                ComplexityLimitReached('Query is too complex')
            if new_depth > max_depth:
                max_depth = new_depth
    return max_depth, selections


class ProtectorBackend(GraphQLCoreBackend):
    depth_limit = None
    selections_limit = None
    complexity_limit = None

    def __init__(
        self, *args,
        depth_limit=20, selections_limit=None, complexity_limit=100, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.depth_limit = depth_limit
        self.selections_limit = selections_limit
        self.complexity_limit = complexity_limit

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
                self.complexity_limit
            )

        return document
