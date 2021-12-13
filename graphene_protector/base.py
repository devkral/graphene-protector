from graphql.execution import ExecutionResult
from graphene.types import Schema as GrapheneSchema
from graphql.error import GraphQLError


import re
from functools import wraps

from dataclasses import dataclass, fields, replace

from typing import Union, List


try:
    from graphql.validation import (
        validate,
        ValidationContext,
        ValidationRule,
    )

    from graphql.language import (
        parse,
        DefinitionNode,
        FragmentSpreadNode,
        OperationDefinitionNode,
    )

    def get_schema(ctx: ValidationContext):
        return ctx.schema

    def get_ast(ctx: ValidationContext):
        return ctx.document

except ImportError:
    from graphql.validation.validation import ValidationContext, validate
    from graphql.validation.rules.base import ValidationRule

    from graphql.language.parser import parse
    from graphql.language.ast import (
        Definition as DefinitionNode,
        FragmentSpread as FragmentSpreadNode,
        OperationDefinition as OperationDefinitionNode,
    )

    def get_schema(ctx: ValidationContext):
        return ctx.get_schema()

    def get_ast(ctx: ValidationContext):
        return ctx.get_ast()


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
    validation_context,
    limits,
    auto_snakecase=False,
    level=0,
):
    # level 0: starts on query level. Every query is level 1
    selections = 0
    max_depth = level
    assert (
        limits.depth is not MISSING
    ), "missing should be already resolved here"
    if limits.depth and max_depth > limits.depth:
        raise DepthLimitReached("Query is too deep")
    for field_orig in selection_set.selections:
        fieldname = field_orig.name.value
        # ignore introspection queries
        if fieldname.startswith("__"):
            continue
        if auto_snakecase and not hasattr(schema, fieldname):
            fieldname = to_snake_case(fieldname)
        if isinstance(field_orig, FragmentSpreadNode):
            field = validation_context.getFragment(field_orig.name.value)
        else:
            field = field_orig
        if field.selection_set:
            schema_field = getattr(schema, fieldname)
            sub_limits = limits_for_field(schema_field, limits)
            new_depth, local_selections = check_resource_usage(
                schema_field.type,
                field.selection_set,
                validation_context,
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


class LimitsValidationRule(ValidationRule):
    def __init__(
        self,
        validation_context: ValidationContext,
        default_limits=None,
    ):
        schema = get_schema(validation_context)
        document: List[DefinitionNode] = get_ast(validation_context)
        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue
            operation_type = definition.operation
            maintype = getattr(schema, f"get_{operation_type}_type")()
            if hasattr(maintype, "graphene_type"):
                maintype = maintype.graphene_type
            check_resource_usage(
                maintype,
                definition.selection_set,
                validation_context,
                default_limits,
                auto_snakecase=getattr(schema, "auto_camelcase", False),
            )


def decorate_limits(fn):
    @wraps(fn)
    def wrapper(superself, query, *args, check_limits=True, **kwargs):
        if check_limits:
            try:
                document_ast = parse(query)
            except GraphQLError as error:
                return ExecutionResult(data=None, errors=[error])

            class TempRule(LimitsValidationRule):
                def __init__(self, validation_context):
                    super().__init__(
                        validation_context, superself.get_default_limits()
                    )

            validation_errors = validate(
                superself.graphql_schema,
                document_ast,
                [TempRule],
            )
            if validation_errors:
                return ExecutionResult(errors=validation_errors, invalid=True)
        return fn(superself, query, *args, **kwargs)

    return wrapper


def decorate_limits_async(fn):
    @wraps(fn)
    async def wrapper(superself, query, *args, check_limits=True, **kwargs):
        if check_limits:
            try:
                document_ast = parse(query)
            except GraphQLError as error:
                return ExecutionResult(data=None, errors=[error])

            class TempRule(LimitsValidationRule):
                def __init__(self, validation_context):
                    super().__init__(
                        validation_context, superself.get_default_limits()
                    )

            validation_errors = validate(
                superself.graphql_schema,
                document_ast,
                [TempRule],
            )
            if validation_errors:
                return ExecutionResult(errors=validation_errors, invalid=True)
        return await fn(superself, query, *args, **kwargs)

    return wrapper


class Schema(GrapheneSchema):
    default_limits = None

    def __init__(self, *args, limits=Limits(), **kwargs):
        self.default_limits = limits
        super().__init__(*args, **kwargs)

    def get_default_limits(self):
        return merge_limits(
            DEFAULT_LIMITS,
            self.default_limits,
        )

    execute = decorate_limits(GrapheneSchema.execute)
    if hasattr(GrapheneSchema, "execute_async"):
        execute_async = decorate_limits_async(GrapheneSchema.execute_async)

    if hasattr(GrapheneSchema, "subscribe"):
        subscribe = decorate_limits_async(GrapheneSchema.subscribe)
