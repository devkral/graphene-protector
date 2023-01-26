import re
from dataclasses import fields, replace
from functools import wraps
from typing import Callable, List, Tuple
from graphql import GraphQLInterfaceType, GraphQLObjectType, GraphQLUnionType

from graphql.error import GraphQLError
from graphql.execution import ExecutionResult
from graphql.language import (
    DefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    Node,
    OperationDefinitionNode,
    parse,
)
from graphql.type.definition import GraphQLType
from graphql.validation import ValidationContext, ValidationRule, validate

from .misc import (
    DEFAULT_LIMITS,
    EarlyStop,
    MISSING,
    MISSING_LIMITS,
    ComplexityLimitReached,
    DepthLimitReached,
    SelectionsLimitReached,
    Limits,
    default_path_ignore_pattern,
)


def follow_of_type(field: GraphQLType) -> GraphQLType:
    while hasattr(field, "of_type"):
        field = getattr(field, "of_type")
    return field


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


def merge_limits(old_limits: Limits, new_limits: Limits):
    # new_limits may have problems after the 0.10 migration
    assert isinstance(new_limits, Limits), "invalid type %s" % type(new_limits)
    _limits = {}
    for field in fields(new_limits):
        value = getattr(new_limits, field.name)
        if value != MISSING:
            _limits[field.name] = value
    return replace(old_limits, **_limits)


def _extract_limits(scheme_field) -> Limits:
    while True:
        if hasattr(scheme_field, "_graphene_protector_limits"):
            return getattr(scheme_field, "_graphene_protector_limits")
        if hasattr(scheme_field, "__func__"):
            scheme_field = getattr(scheme_field, "__func__")
        else:
            break
    return MISSING_LIMITS


def limits_for_field(field, old_limits, **kwargs) -> Tuple[Limits, Limits]:
    # retrieve optional limitation attributes defined for the current
    # operation
    effective_limits = _extract_limits(field)
    if effective_limits is MISSING_LIMITS:
        return old_limits, MISSING_LIMITS
    return merge_limits(old_limits, effective_limits), effective_limits


_default_path_ignore_pattern = re.compile(default_path_ignore_pattern)


def check_resource_usage(
    schema,
    node: Node,
    validation_context: ValidationContext,
    limits: Limits,
    on_error: Callable[[GraphQLError], None],
    auto_snakecase=False,
    path_ignore_pattern: re.Pattern = _default_path_ignore_pattern,
    get_limits_for_field=limits_for_field,
    level_depth=0,
    level_complexity=0,
    _seen_limits=None,
    _path="",
) -> Tuple[int, int, int]:
    if _seen_limits is None:
        _seen_limits = set()
    # level 0: starts on query level. Every query is level 1
    selections = 0
    max_level_depth = level_depth
    max_level_complexity = level_complexity
    assert (
        limits.depth is not MISSING
    ), "missing should be already resolved here"
    if limits.depth and max_level_depth > limits.depth:
        on_error(
            DepthLimitReached(
                "Query is too deep",
            )
        )
    for field in node.selection_set.selections:
        if isinstance(field, InlineFragmentNode):
            fieldname = field.type_condition.name.value
        else:
            fieldname = field.name.value
        # ignore introspection queries
        if fieldname.startswith("__"):
            continue
        if auto_snakecase and not hasattr(schema, fieldname):
            fieldname = to_snake_case(fieldname)
        if isinstance(field, FragmentSpreadNode):
            field = validation_context.get_fragment(field.name.value)

        if isinstance(field, (GraphQLUnionType, GraphQLInterfaceType)):
            merged_limits = limits
            local_selections = 0

            count_this_field = True
            _npath = f"{_path}/{fieldname}"
            if path_ignore_pattern.match(_npath):
                count_this_field = False
            for field_type in validation_context.schema.get_possible_types(
                field
            ):
                (
                    new_depth,
                    new_depth_complexity,
                    local2_selections,
                ) = check_resource_usage(
                    follow_of_type(field_type),
                    field,
                    validation_context,
                    merged_limits,
                    on_error=on_error,
                    auto_snakecase=auto_snakecase,
                    path_ignore_pattern=path_ignore_pattern,
                    get_limits_for_field=get_limits_for_field,
                    level_depth=level_depth + 1
                    if count_this_field
                    else level_depth,
                    # don't increase complexity, in unions it stays the same
                    level_complexity=level_complexity,
                    _seen_limits=_seen_limits,
                    _path=_npath,
                )

                # we know here, that there are no individual sub_limits

                # called per query, selection
                if (
                    merged_limits.complexity
                    and (new_depth_complexity - level_complexity)
                    * local2_selections
                    > merged_limits.complexity
                ):
                    on_error(
                        ComplexityLimitReached("Query is too complex", node)
                    )
                # find max of selections for unions
                if local2_selections > local_selections:
                    local_selections = local2_selections
                if new_depth > max_level_depth:
                    max_level_depth = new_depth
                if new_depth_complexity > max_level_complexity:
                    max_level_complexity = new_depth_complexity
            # ignore union fields itself for selection_count
            # because we have depth for that
            selections += local_selections
        elif field.selection_set:
            try:
                schema_field = getattr(schema, fieldname)
            except AttributeError:
                _name = None
                if hasattr(field, "name"):
                    _name = field.name
                    if hasattr(_name, "value"):
                        _name = _name.value
                if (
                    hasattr(schema, "fields")
                    and not isinstance(schema, GraphQLInterfaceType)
                    and _name
                ):
                    schema_field = schema.fields[_name]
                else:
                    schema_field = schema
            merged_limits, sub_limits = get_limits_for_field(
                schema_field,
                limits,
                parent=schema,
                fieldname=fieldname,
            )
            allow_reset = True
            count_this_field = True
            _npath = f"{_path}/{fieldname}"
            if path_ignore_pattern.match(_npath):
                count_this_field = False
            # must be seperate from condition above
            if sub_limits is not MISSING:
                if id(sub_limits) in _seen_limits:
                    allow_reset = False
                else:
                    _seen_limits.add(id(sub_limits))
            if isinstance(
                schema_field,
                (GraphQLUnionType, GraphQLInterfaceType, GraphQLObjectType),
            ):
                sub_field_type = schema_field
            else:
                sub_field_type = follow_of_type(schema_field.type)
            (
                new_depth,
                new_depth_complexity,
                local_selections,
            ) = check_resource_usage(
                sub_field_type,
                field,
                validation_context,
                merged_limits,
                on_error=on_error,
                auto_snakecase=auto_snakecase,
                path_ignore_pattern=path_ignore_pattern,
                get_limits_for_field=get_limits_for_field,
                # count_this_field will be casted in 1 for True
                level_depth=level_depth + count_this_field
                if sub_limits.depth is MISSING or not allow_reset
                else 1,
                level_complexity=level_complexity + count_this_field
                if sub_limits.complexity is MISSING or not allow_reset
                else 1,
                _seen_limits=_seen_limits,
                _path=_npath,
            )
            # called per query, selection
            if (
                merged_limits.complexity
                and (new_depth - level_depth) * local_selections
                > merged_limits.complexity
            ):
                on_error(ComplexityLimitReached("Query is too complex", node))
            # increase level counter only if limits are not redefined
            if sub_limits.depth is MISSING and new_depth > max_level_depth:
                max_level_depth = new_depth
            if (
                sub_limits.complexity is MISSING
                and new_depth_complexity > max_level_complexity
            ):
                max_level_complexity = new_depth_complexity

            # ignore fields with selection_set itself for selection_count
            # because we have depth for that
            if sub_limits.selections is MISSING:
                selections += local_selections
        else:
            count_this_field = True
            if path_ignore_pattern.match(_path):
                count_this_field = False
            # count_this_field will be casted in 1 for True
            selections += count_this_field

        if limits.selections and selections > limits.selections:
            on_error(SelectionsLimitReached("Query selects too much", node))
    return max_level_depth, max_level_complexity, selections


class LimitsValidationRule(ValidationRule):
    default_limits = None
    path_ignore_pattern = None
    full_validation = None
    # TODO: find out if auto_camelcase is set
    # But no priority as this code works also
    auto_snakecase = True

    def __init__(self, context):
        super().__init__(context)
        schema = self.context.schema
        # if not set use schema to get defaults or set in case no limits
        # are found to DEFAULT:LIMITS
        if not self.default_limits:
            self.default_limits = getattr(
                schema, "get_protector_default_limits", lambda: DEFAULT_LIMITS
            )()
        if not self.path_ignore_pattern:
            self.path_ignore_pattern = getattr(
                schema,
                "get_protector_path_ignore_pattern",
                lambda: default_path_ignore_pattern,
            )()
            if not isinstance(self.path_ignore_pattern, re.Pattern):
                self.path_ignore_pattern = re.compile(self.path_ignore_pattern)
        if self.full_validation is None:
            self.full_validation = getattr(
                schema,
                "get_protector_full_validation",
                lambda: False,
            )()

    def enter(self, node, key, parent, path, ancestors):
        if parent is not None:
            return None
        schema = self.context.schema

        document: List[DefinitionNode] = self.context.document
        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue
            operation_type = definition.operation.name.title()
            maintype = schema.get_type(operation_type)
            assert maintype is not None
            get_limits_for_field = limits_for_field
            if hasattr(maintype, "graphene_type"):
                maintype = maintype.graphene_type
            if hasattr(schema, "_strawberry_schema"):

                def get_limits_for_field(
                    field, old_limits, parent, fieldname, **kwargs
                ):
                    name = follow_of_type(parent).name
                    definition = (
                        schema._strawberry_schema.schema_converter.type_map[
                            name
                        ]
                    ).definition
                    # e.g. union
                    if not hasattr(definition, "get_field"):
                        return limits_for_field(definition, old_limits)

                    nfield = definition.get_field(fieldname)
                    return limits_for_field(nfield, old_limits)

            try:
                check_resource_usage(
                    maintype,
                    definition,
                    self.context,
                    self.default_limits,
                    self.report_error,
                    get_limits_for_field=get_limits_for_field,
                    auto_snakecase=self.auto_snakecase,
                    path_ignore_pattern=self.path_ignore_pattern,
                )
            except EarlyStop:
                pass

    def report_error(self, error):
        self.context.report_error(error)
        if not self.full_validation:
            raise EarlyStop()


_rules = [LimitsValidationRule]


def _decorate_limits_helper(superself, args, kwargs):
    check_limits = kwargs.pop("check_limits", True)
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
            schema.get_protector_default_limits = (
                superself.get_protector_default_limits
            )
            schema.get_protector_path_ignore_pattern = (
                superself.get_protector_path_ignore_pattern
            )
            schema.get_protector_full_validation = (
                superself.get_protector_full_validation
            )

            return validate(
                schema,
                document_ast,
                _rules,
            )
    return []


def decorate_limits(fn):
    @wraps(fn)
    def wrapper(superself, *args, **kwargs):
        validation_errors = _decorate_limits_helper(superself, args, kwargs)
        if validation_errors:
            return ExecutionResult(errors=validation_errors)
        return fn(superself, *args, **kwargs)

    return wrapper


def decorate_limits_async(fn):
    @wraps(fn)
    async def wrapper(superself, *args, **kwargs):
        validation_errors = _decorate_limits_helper(superself, args, kwargs)
        if validation_errors:
            return ExecutionResult(errors=validation_errors)
        return await fn(superself, *args, **kwargs)

    return wrapper


class SchemaMixin:
    # better fail then omitting limits
    protector_default_limits = None
    protector_path_ignore_pattern = default_path_ignore_pattern

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

    def get_protector_default_limits(self):
        return merge_limits(
            DEFAULT_LIMITS,
            self.protector_default_limits,
        )

    def get_protector_path_ignore_pattern(self):
        return self.protector_path_ignore_pattern

    def get_protector_full_validation(self):
        return False
