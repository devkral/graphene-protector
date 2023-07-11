__package__ = "tests"

import base64
import unittest

from graphene.types import Schema as GrapheneSchema
from graphql_relay import to_global_id

from graphene_protector import Limits
from graphene_protector.graphene import Schema as ProtectorSchema

from .graphene.schema import Query, SomeNode


class TestGraphene(unittest.TestCase):
    def test_simple(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
            types=[SomeNode],
        )
        self.assertIsInstance(schema, GrapheneSchema)
        result = schema.execute("{ hello }")
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})

    def test_node(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None),
            types=[SomeNode],
        )
        self.assertIsInstance(schema, GrapheneSchema)
        result = schema.execute(
            """{ node(id: "%s") { id } }""" % to_global_id("SomeNode", "foo")
        )
        self.assertFalse(result.errors)
        self.assertDictEqual(
            result.data, {"node": {"id": to_global_id("SomeNode", "foo")}}
        )
