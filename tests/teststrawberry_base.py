__package__ = "tests"

import unittest

from graphene_protector import Limits, SchemaMixin
from graphene_protector.strawberry import (
    Schema as ProtectorSchema,
    CustomGrapheneProtector,
)

#
from strawberry import Schema as StrawberrySchema
from .strawberry.schema import Query


class CustomSchema(SchemaMixin, StrawberrySchema):
    default_limits = Limits(depth=2, selections=None, complexity=None)


class TestStrawberry(unittest.IsolatedAsyncioTestCase):
    def test_simple_sync(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = schema.execute_sync(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {name}
            } }"""
        )
        self.assertFalse(result.errors)
        self.assertDictEqual(
            result.data, {"persons": [{"name": "Hans"}, {"name": "Zoe"}]}
        )

    def test_in_out(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = schema.execute_sync('{ inOut(into: ["a", "b"]) }')
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"inOut": ["a", "b"]})

    async def test_simple_async(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {name}
            } }"""
        )
        self.assertFalse(result.errors)
        self.assertDictEqual(
            result.data, {"persons": [{"name": "Hans"}, {"name": "Zoe"}]}
        )

    async def test_async_custom(self):
        schema = CustomSchema(
            query=Query,
            extensions=[CustomGrapheneProtector()],
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {name}
            } }"""
        )
        self.assertFalse(result.errors)
        self.assertDictEqual(
            result.data, {"persons": [{"name": "Hans"}, {"name": "Zoe"}]}
        )
