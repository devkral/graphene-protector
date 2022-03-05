import re
from dataclasses import dataclass, fields, replace
from functools import wraps
from typing import List, Union

from graphql.error import GraphQLError
from graphql.execution import ExecutionResult as GraphqlExecutionResult

try:
    from graphql.language import (
        DefinitionNode,
        FragmentSpreadNode,
        OperationDefinitionNode,
        parse,
    )
    from graphql.validation import ValidationContext, ValidationRule, validate

    ExecutionResult = GraphqlExecutionResult

    def get_schema(ctx: ValidationContext):
        return ctx.schema

    def get_ast(ctx: ValidationContext):
        return ctx.document

    def get_optype(schema, definition):
        operation_type = definition.operation.name.title()
        return schema.get_type(operation_type)

except ImportError:
    from graphql.language.ast import (
        Definition as DefinitionNode,
        FragmentSpread as FragmentSpreadNode,
        OperationDefinition as OperationDefinitionNode,
    )
    from graphql.language.parser import parse
    from graphql.validation.rules.base import ValidationRule
    from graphql.validation.validation import ValidationContext, validate

    class ExecutionResult(GraphqlExecutionResult):
        def __init__(self, data=None, errors=None, extensions=None):
            super().__init__(
                data=data,
                errors=errors,
                extensions=extensions,
                invalid=bool(errors),
            )

    def get_schema(ctx: ValidationContext):
        return ctx.get_schema()

    def get_ast(ctx: ValidationContext):
        return ctx.get_ast()

    def get_optype(schema, definition):
        operation_type = definition.operation.title()
        return schema.get_type(operation_type)


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


class ResourceLimitReached(GraphQLError):
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


def limits_for_field(field, old_limits, **kwargs):
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
    node,
    validation_context,
    limits,
    on_error,
    auto_snakecase=False,
    get_limits_for_field=limits_for_field,
    level=0,
):
    # level 0: starts on query level. Every query is level 1
    selections = 0
    max_depth = level
    assert (
        limits.depth is not MISSING
    ), "missing should be already resolved here"
    if limits.depth and max_depth > limits.depth:
        on_error(
            DepthLimitReached(
                "Query is too deep",
            )
        )
    for field_orig in node.selection_set.selections:
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
            try:
                schema_field = getattr(schema, fieldname)
            except AttributeError:
                schema_field = schema
                if hasattr(schema_field, "of_type"):
                    schema_field = schema_field.of_type

                if hasattr(schema_field, "fields"):
                    schema_field = schema_field.fields[fieldname]
            sub_limits = get_limits_for_field(
                schema_field, limits, parent=schema, fieldname=fieldname
            )
            new_depth, local_selections = check_resource_usage(
                schema_field.type,
                field,
                validation_context,
                sub_limits,
                on_error=on_error,
                auto_snakecase=auto_snakecase,
                get_limits_for_field=get_limits_for_field,
                level=level + 1,
            )
            # called per query, selection
            if (
                sub_limits.complexity
                and (new_depth - level) * local_selections
                > sub_limits.complexity
            ):
                on_error(ComplexityLimitReached("Query is too complex", node))
            # ignore selection_set fields because we have depth for that
            selections += local_selections
            if new_depth > max_depth:
                max_depth = new_depth
        else:
            selections += 1

        if limits.selections and selections > limits.selections:
            on_error(SelectionsLimitReached("Query selects too much", node))
    return max_depth, selections


class LimitsValidationRule(ValidationRule):
    default_limits = None
    # TODO: find out if auto_camelcase is set
    # But no priority as this code works also
    auto_snakecase = True

    def __init__(self, context):
        super().__init__(context)
        schema = get_schema(self.context)
        # if not set use schema to get defaults or set in case no limits
        # are found to DEFAULT:LIMITS
        if not self.default_limits:
            self.default_limits = getattr(
                schema, "get_default_limits", lambda: DEFAULT_LIMITS
            )()

    def enter(self, node, key, parent, path, ancestors):
        if parent is not None:
            return None
        schema = get_schema(self.context)

        document: List[DefinitionNode] = get_ast(self.context)
        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue
            maintype = get_optype(schema, definition)
            get_limits_for_field = limits_for_field
            if hasattr(maintype, "graphene_type"):
                maintype = maintype.graphene_type
            if hasattr(schema, "_strawberry_schema"):

                def get_limits_for_field(
                    field, old_limits, parent, fieldname, **kwargs
                ):
                    try:
                        name = parent.name
                    except AttributeError:
                        name = parent.of_type.name
                    definition = (
                        schema._strawberry_schema.schema_converter.type_map[
                            name
                        ]
                    ).definition
                    nfield = definition.get_field(fieldname)
                    return limits_for_field(nfield, old_limits)

            check_resource_usage(
                maintype,
                definition,
                self.context,
                self.default_limits,
                self.report_error,
                get_limits_for_field=get_limits_for_field,
                auto_snakecase=self.auto_snakecase,
            )

    if not hasattr(ValidationRule, "report_error"):

        def report_error(self, error):
            self.context.report_error(error)


_rules = [LimitsValidationRule]


def decorate_limits(fn):
    @wraps(fn)
    def wrapper(superself, *args, check_limits=True, **kwargs):
        if check_limits and (kwargs.get("query") or len(args)):
            try:
                query = kwargs.get("query", args[0])
            except IndexError:
                pass
            if query:
                try:
                    document_ast = parse(query)
                except GraphQLError as error:
                    return ExecutionResult(data=None, errors=[error])
                if hasattr(superself, "graphql_schema"):
                    schema = getattr(superself, "graphql_schema")
                elif hasattr(superself, "_schema"):
                    schema = getattr(superself, "_schema")
                else:
                    schema = superself
                schema.get_default_limits = superself.get_default_limits

                validation_errors = validate(
                    schema,
                    document_ast,
                    _rules,
                )
                if validation_errors:
                    return ExecutionResult(errors=validation_errors)
        return fn(superself, *args, **kwargs)

    return wrapper


def decorate_limits_async(fn):
    decorated = decorate_limits(fn)

    @wraps(fn)
    async def wrapper(superself, *args, **kwargs):
        return await decorated(superself, *args, **kwargs)

    return wrapper


class SchemaMixin:
    default_limits = None

    def __init_subclass__(cls, **kwargs):
        if hasattr(cls, "execute_sync"):
            cls.execute_sync = decorate_limits(cls.execute_sync)
            if hasattr(cls, "execute"):
                cls.execute = decorate_limits_async(cls.execute)
        else:
            if hasattr(cls, "execute"):
                cls.execute = decorate_limits(cls.execute)
            if hasattr(cls, "execute_async"):
                cls.execute_async = decorate_limits_async(cls.execute_async)
        if hasattr(cls, "subscribe"):
            cls.subscribe = decorate_limits_async(cls.subscribe)

    def get_default_limits(self):
        return merge_limits(
            DEFAULT_LIMITS,
            self.default_limits,
        )
