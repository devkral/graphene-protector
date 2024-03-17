__all__ = [
    "follow_of_type",
    "to_camel_case",
    "to_snake_case",
    "merge_limits",
    "gas_for_field",
    "limits_for_field",
    "check_resource_usage",
    "gas_usage",
    "LimitsValidationRule",
    "decorate_limits",
    "decorate_limits_async",
    "SchemaMixin",
]

import re
from collections.abc import Callable
from dataclasses import fields, replace
from functools import partial, wraps
from typing import List, Tuple, Union

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
    MISSING,
    MISSING_LIMITS,
    ComplexityLimitReached,
    DepthLimitReached,
    EarlyStop,
    GasLimitReached,
    Limits,
    SelectionsLimitReached,
    UsagesResult,
    default_path_ignore_pattern,
)

_default_path_ignore_pattern = re.compile(default_path_ignore_pattern)
_empty = frozenset()


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
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])


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
        # passthrough is always set so there is no issue
        if value is not MISSING:
            _limits[field.name] = value
    return replace(old_limits, **_limits)


def _extract_limits(schema_field) -> Limits:
    while True:
        if hasattr(schema_field, "_graphene_protector_limits"):
            return getattr(schema_field, "_graphene_protector_limits")
        if hasattr(schema_field, "__func__"):
            schema_field = getattr(schema_field, "__func__")
        else:
            break
    return MISSING_LIMITS


def gas_for_field(schema_field, **kwargs) -> int:
    while True:
        if hasattr(schema_field, "_graphene_protector_gas"):
            retval = getattr(schema_field, "_graphene_protector_gas")
            if callable(retval):
                retval = retval(schema_field=schema_field, **kwargs)
            return retval
        if hasattr(schema_field, "__func__"):
            schema_field = getattr(schema_field, "__func__")
        else:
            break
    return 0


def limits_for_field(field, old_limits, **kwargs) -> Tuple[Limits, Limits]:
    # retrieve optional limitation attributes defined for the current
    # operation
    effective_limits = _extract_limits(field)
    if effective_limits is MISSING_LIMITS:
        return old_limits, MISSING_LIMITS
    return merge_limits(old_limits, effective_limits), effective_limits


def _check_resource_usage(
    schema,
    node: Node,
    validation_context: ValidationContext,
    *,
    limits: Limits,
    on_error: Callable[[GraphQLError], None],
    get_result,
    get_limits_for_field,
    get_gas_for_field,
    seen_limits,
    graphql_path,
    level_depth,
    level_complexity,
    auto_snakecase=False,
    camelcase_path=True,
    path_ignore_pattern: re.Pattern = _default_path_ignore_pattern,
) -> UsagesResult:
    # level 0: starts on query level. Every query is level 1
    retval = UsagesResult(
        max_level_depth=level_depth,
        max_level_complexity=level_complexity,
    )
    assert limits.depth is not MISSING, "missing should be already resolved here"
    if limits.depth and retval.max_level_depth > limits.depth:
        on_error(DepthLimitReached("Query is too deep", used_resources=retval))
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

        # add gas for field
        retval.gas_used += get_gas_for_field(
            schema_field, parent=schema, fieldname=fieldname, graphql_path=graphql_path
        )

        if isinstance(field, (GraphQLUnionType, GraphQLInterfaceType)):
            merged_limits = limits
            local_union_selections = 0
            local_gas = 0

            field_contributes_to_score = True
            _npath = "{}/{}".format(
                graphql_path,
                to_camel_case(fieldname) if camelcase_path else fieldname,
            )
            if path_ignore_pattern.match(_npath):
                field_contributes_to_score = False
            for field_type in validation_context.schema.get_possible_types(field):
                yield partial(
                    _check_resource_usage,
                    follow_of_type(field_type),
                    field,
                    validation_context,
                    limits=merged_limits,
                    on_error=on_error,
                    auto_snakecase=auto_snakecase,
                    camelcase_path=camelcase_path,
                    path_ignore_pattern=path_ignore_pattern,
                    get_limits_for_field=get_limits_for_field,
                    get_gas_for_field=get_gas_for_field,
                    level_depth=level_depth + 1
                    if field_contributes_to_score
                    else level_depth,
                    # don't increase complexity, in unions it stays the same
                    level_complexity=level_complexity,
                    seen_limits=seen_limits,
                    graphql_path=_npath,
                    get_result=get_result,
                )
                local_result = get_result()

                # we know here, that there are no individual sub_limits

                # called per query, selection
                if (
                    merged_limits.complexity
                    and (local_result.max_level_complexity - level_complexity)
                    * local_result.selections
                    > merged_limits.complexity
                ):
                    on_error(
                        ComplexityLimitReached(
                            "Query is too complex",
                            node,
                            used_resources=replace(
                                retval,
                                max_level_complexity=(
                                    local_result.max_level_complexity - level_complexity
                                )
                                * local_result.selections,
                            ),
                        )
                    )
                # find max of selections for unions
                if local_result.selections > local_union_selections:
                    local_union_selections = local_result.selections
                # find max of selections for unions
                if local_result.gas_used > local_gas:
                    local_gas = local_result.gas_used
                if local_result.max_level_depth > retval.max_level_depth:
                    retval.max_level_depth = local_result.max_level_depth
                if local_result.max_level_complexity > retval.max_level_complexity:
                    retval.max_level_complexity = local_result.max_level_complexity
            # ignore union fields itself for selection_count
            # because we have depth for that
            retval.selections += local_union_selections
            # gas for field itself already calculated in parent field.selection_set
            retval.gas_used += local_gas
            del local_union_selections
            del local_gas
        elif field.selection_set:
            merged_limits, sub_limits = get_limits_for_field(
                schema_field,
                limits,
                parent=schema,
                fieldname=fieldname,
                graphql_path=graphql_path,
            )
            allow_restart_counters = True
            field_contributes_to_score = True
            _npath = "{}/{}".format(
                graphql_path,
                to_camel_case(fieldname) if camelcase_path else fieldname,
            )
            if path_ignore_pattern.match(_npath):
                field_contributes_to_score = False
            # must be seperate from condition above
            if sub_limits is not MISSING:
                id_sub_limits = id(sub_limits)
                # loop detected, cannot reset via sub_limits
                if id_sub_limits in seen_limits:
                    allow_restart_counters = False
                else:
                    seen_limits.add(id_sub_limits)
            if isinstance(
                schema_field,
                (GraphQLUnionType, GraphQLInterfaceType, GraphQLObjectType),
            ) or not hasattr(schema_field, "type"):
                sub_field_type = schema_field
            else:
                sub_field_type = follow_of_type(schema_field.type)
            yield partial(
                _check_resource_usage,
                sub_field_type,
                field,
                validation_context,
                limits=merged_limits,
                on_error=on_error,
                auto_snakecase=auto_snakecase,
                camelcase_path=camelcase_path,
                path_ignore_pattern=path_ignore_pattern,
                get_limits_for_field=get_limits_for_field,
                get_gas_for_field=get_gas_for_field,
                # field_contributes_to_score will be casted to 1 for True
                level_depth=level_depth + field_contributes_to_score
                if sub_limits.depth is MISSING or not allow_restart_counters
                else 1,
                level_complexity=level_complexity + field_contributes_to_score
                if sub_limits.complexity is MISSING or not allow_restart_counters
                else 1,
                seen_limits=seen_limits,
                graphql_path=_npath,
                get_result=get_result,
            )
            local_result = get_result()
            # called per query, selection
            if (
                merged_limits.complexity
                and (local_result.max_level_depth - level_depth)
                * local_result.selections
                > merged_limits.complexity
            ):
                on_error(
                    ComplexityLimitReached(
                        "Query is too complex",
                        node,
                        used_resources=replace(
                            retval,
                            max_level_complexity=(
                                local_result.max_level_depth - level_depth
                            )
                            * local_result.selections,
                        ),
                    )
                )
            # increase level counter only if limits are not redefined
            if (
                sub_limits.depth is MISSING or "depth" in sub_limits.passthrough
            ) and local_result.max_level_depth > retval.max_level_depth:
                retval.max_level_depth = local_result.max_level_depth
            if (
                sub_limits.complexity is MISSING
                or "complexity" in sub_limits.passthrough
            ) and local_result.max_level_complexity > retval.max_level_complexity:
                retval.max_level_complexity = local_result.max_level_complexity

            # ignore fields with selection_set itself for selection_count
            # because we have depth for that
            if (
                sub_limits.selections is MISSING
                or "selections" in sub_limits.passthrough
            ):
                retval.selections += local_result.selections
            if sub_limits.gas is MISSING or "gas" in sub_limits.passthrough:
                retval.gas_used += local_result.gas_used
            del schema_field
        else:
            # gas for field itself already calculated in parent field.selection_set
            if not path_ignore_pattern.match(graphql_path):
                # field_contributes_to_score
                retval.selections += 1

        if limits.selections and retval.selections > limits.selections:
            on_error(
                SelectionsLimitReached(
                    "Query selects too much", node, used_resources=retval
                )
            )
        if limits.gas and retval.gas_used > limits.gas:
            on_error(
                GasLimitReached("Query uses too much gas", node, used_resources=retval)
            )
    yield retval


def check_resource_usage(
    schema,
    node: Node,
    validation_context: ValidationContext,
    *,
    limits: Limits,
    on_error: Callable[[GraphQLError], None],
    auto_snakecase=False,
    camelcase_path=True,
    path_ignore_pattern: re.Pattern = _default_path_ignore_pattern,
    get_limits_for_field=limits_for_field,
    get_gas_for_field=gas_for_field,
):
    result_stack = []
    seen_limits = set()

    fn_stack = [
        _check_resource_usage(
            schema,
            node,
            validation_context,
            limits=limits,
            on_error=on_error,
            auto_snakecase=auto_snakecase,
            camelcase_path=camelcase_path,
            path_ignore_pattern=path_ignore_pattern,
            get_gas_for_field=get_gas_for_field,
            get_limits_for_field=get_limits_for_field,
            seen_limits=seen_limits,
            get_result=result_stack.pop,
            graphql_path="",
            level_depth=0,
            level_complexity=0,
        )
    ]

    while fn_stack:
        cur_el = fn_stack[-1]
        try:
            next_el = next(cur_el)
            if isinstance(next_el, partial):
                fn_stack.append(next_el())
            else:
                result_stack.append(next_el)
        except StopIteration:
            fn_stack.pop()
    return result_stack.pop()


def gas_usage(gas_used: Union[Callable[[], int], int]):
    def wrapper(schema_field):
        setattr(schema_field, "_graphene_protector_gas", gas_used)
        return schema_field

    return wrapper


class LimitsValidationRule(ValidationRule):
    default_limits = None
    path_ignore_pattern = None
    full_validation = None
    # TODO: find out if auto_camelcase is set
    # But no priority as this code works also
    auto_snakecase = None
    camelcase_path = None

    def __init__(self, context):
        super().__init__(context)
        schema = self.context.schema
        # if not set use schema to get defaults or set in case no limits
        # are found to DEFAULT:LIMITS
        if not self.default_limits:
            self.default_limits = getattr(
                schema,
                "get_protector_default_limits",
                lambda: DEFAULT_LIMITS,
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
        if self.auto_snakecase is None:
            self.auto_snakecase = getattr(
                schema,
                "get_protector_auto_snakecase",
                lambda: True,
            )()

        if self.camelcase_path is None:
            self.camelcase_path = getattr(
                schema,
                "get_protector_camelcase_path",
                lambda: self.auto_snakecase,
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
            get_gas_for_field = gas_for_field
            if hasattr(maintype, "graphene_type"):
                maintype = maintype.graphene_type
            if hasattr(schema, "_strawberry_schema"):

                def get_limits_for_field(
                    field, old_limits, parent, fieldname, **kwargs
                ):
                    name = follow_of_type(parent).name
                    definition = (
                        schema._strawberry_schema.schema_converter.type_map[name]
                    ).definition
                    # e.g. union
                    if not hasattr(definition, "get_field"):
                        return limits_for_field(definition, old_limits)

                    nfield = definition.get_field(fieldname)
                    return limits_for_field(nfield, old_limits)

                def get_gas_for_field(field, parent, fieldname, **kwargs):
                    name = follow_of_type(parent).name
                    definition = (
                        schema._strawberry_schema.schema_converter.type_map[name]
                    ).definition
                    # e.g. union
                    if not hasattr(definition, "get_field"):
                        return gas_for_field(definition)

                    nfield = definition.get_field(fieldname)
                    return gas_for_field(nfield)

            if getattr(self, "protector_on", True):
                try:
                    check_resource_usage(
                        maintype,
                        definition,
                        self.context,
                        limits=self.default_limits,
                        on_error=self.report_error,
                        get_limits_for_field=get_limits_for_field,
                        get_gas_for_field=get_gas_for_field,
                        auto_snakecase=self.auto_snakecase,
                        camelcase_path=self.camelcase_path,
                        path_ignore_pattern=self.path_ignore_pattern,
                    )
                except EarlyStop:
                    pass

    def report_error(self, error):
        self.context.report_error(error)
        if not self.full_validation:
            raise EarlyStop()


_rules = [LimitsValidationRule]


def _decorate_limits_helper(
    superself, args, kwargs, protector_per_operation_validation
):
    check_limits = kwargs.pop("check_limits", True)
    if kwargs.get("query") or len(args):
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
            # required for protector_per_operation_validation = False
            superself.protector_decorate_graphql_schema(schema)
            if check_limits:
                if protector_per_operation_validation:
                    return validate(
                        schema,
                        document_ast,
                        _rules,
                    )
            else:
                schema.protector_on = False
    return _empty


def decorate_limits(fn, protector_per_operation_validation):
    @wraps(fn)
    def wrapper(superself, *args, **kwargs):
        validation_errors = _decorate_limits_helper(
            superself, args, kwargs, protector_per_operation_validation
        )
        if validation_errors:
            return ExecutionResult(errors=validation_errors)
        return fn(superself, *args, **kwargs)

    return wrapper


def decorate_limits_async(fn, protector_per_operation_validation):
    @wraps(fn)
    async def wrapper(superself, *args, **kwargs):
        validation_errors = _decorate_limits_helper(
            superself, args, kwargs, protector_per_operation_validation
        )
        if validation_errors:
            return ExecutionResult(errors=validation_errors)
        return await fn(superself, *args, **kwargs)

    return wrapper


class SchemaMixin:
    # better fail then omitting limits
    protector_default_limits = None
    protector_path_ignore_pattern = default_path_ignore_pattern

    def __init_subclass__(cls, protector_per_operation_validation=True, **kwargs):
        if hasattr(cls, "execute_sync"):
            cls.execute_sync = decorate_limits(
                cls.execute_sync, protector_per_operation_validation
            )
            if hasattr(cls, "execute"):
                cls.execute = decorate_limits_async(
                    cls.execute, protector_per_operation_validation
                )
        else:
            if hasattr(cls, "execute"):
                cls.execute = decorate_limits(
                    cls.execute, protector_per_operation_validation
                )
            if hasattr(cls, "execute_async"):
                cls.execute_async = decorate_limits_async(
                    cls.execute_async, protector_per_operation_validation
                )
        if hasattr(cls, "subscribe"):
            cls.subscribe = decorate_limits_async(
                cls.subscribe, protector_per_operation_validation
            )

    def protector_decorate_graphql_schema(self, schema):
        for funcname in (
            "get_protector_default_limits",
            "get_protector_path_ignore_pattern",
            "get_protector_full_validation",
            "get_protector_auto_snakecase",
            "get_protector_camelcase_path",
        ):
            schema.protector_on = True
            setattr(schema, funcname, getattr(self, funcname))

    def get_protector_default_limits(self):
        return merge_limits(
            DEFAULT_LIMITS,
            self.protector_default_limits,
        )

    def get_protector_path_ignore_pattern(self):
        return self.protector_path_ignore_pattern

    def get_protector_full_validation(self):
        return False

    def get_protector_auto_snakecase(self):
        return True

    def get_protector_camelcase_path(self):
        return self.get_protector_auto_snakecase()
