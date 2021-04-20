from inspect import getmembers
from graphql.backend.core import GraphQLCoreBackend
from graphql.language.ast import (
    FragmentDefinition,
    FragmentSpread,
    OperationDefinition
)


class Settings:
    depth_limit = 20
    selections_limit = None
    complexity_limit = 100

    def __init__(self, *args, **kwargs):
        # For every self attribute, get same attribute's name from kwargs, and save it if it exists
        # Alternatively, use the already set value
        # ie. if depth_limit=1 has been given as a kwarg, it will be saved as self.depth_limit
        # else, self.depth_limit will be used as default value
        for attribute, value in getmembers(self):
            if not callable(attribute) and not attribute.startswith('_'):
                self.__dict__[attribute] = kwargs.get(attribute, value)


class Limits:
    depth = None
    selections = None
    complexity = None

    _settings = Settings()

    def __init_subclass__(cls, settings=_settings):
        cls._settings = settings

    def __init__(self, *args, **kwargs):
        # For every self attribute, get same attribute's name from kwargs, and save it if it exists
        # Alternatively, use default value from the settings
        # ie. if depth=1 has been given as a kwarg, it will be saved as self.depth
        # else, self._settings.depth will be used as default value
        for attribute, value in getmembers(self):
            if not callable(attribute) and not attribute.startswith('_'):
                self.__dict__[attribute] = kwargs.get(
                    attribute, self._settings.__dict__[f'{attribute}_limit']
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
                self.default_limits.depth,
                self.default_limits.selections,
                self.default_limits.complexity
            )

        return document
