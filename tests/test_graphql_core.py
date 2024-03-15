__package__ = "tests"

import unittest

from graphql import parse, validate
from graphql.type import GraphQLSchema

from graphene_protector import Limits, LimitsValidationRule, SchemaMixin

from .graphql.schema import Query


class Schema(GraphQLSchema, SchemaMixin):
    protector_default_limits = Limits(depth=2, selections=None, complexity=None, gas=1)
    auto_camelcase = False


class TestCore(unittest.TestCase):
    def test_simple(self):
        schema = Schema(
            query=Query,
        )
        query_ast = parse("{ hello }")
        self.assertFalse(validate(schema, query_ast, [LimitsValidationRule]))
        query_ast = parse("{ hello, hello1: hello }")
        self.assertTrue(validate(schema, query_ast, [LimitsValidationRule]))
