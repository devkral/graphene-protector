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
    def test_simple(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = schema.execute_sync("{ hello }")
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})

    async def test_async(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute("{ hello }")
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})

    async def test_async_custom(self):
        schema = CustomSchema(
            query=Query,
            extensions=[CustomGrapheneProtector()],
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute("{ hello }")
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})
