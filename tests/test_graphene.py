__package__ = "tests"

import unittest

from graphene_protector import Limits
from graphene_protector.graphene import Schema as ProtectorSchema

#
from graphene.types import Schema as GrapheneSchema
from .graphene.schema import Query


class TestGraphene(unittest.TestCase):
    def test_simple(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, GrapheneSchema)
        result = schema.execute("{ hello }")
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})
