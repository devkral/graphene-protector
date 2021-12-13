__package__ = "tests"

import unittest

from graphene_protector import Limits, Schema as ProtectorSchema

#
from graphene.types import Schema as GrapheneSchema
from .graphql.schema import schema


class TestCore(unittest.TestCase):
    def test_simple(self):
        s = ProtectorSchema(
            limits=Limits(depth=2, selections=None, complexity=None)
        )
        self.assertIsInstance(s, GrapheneSchema)
        result = s.execute(schema, "{ hello }")
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})
