__package__ = "tests"

import unittest

from graphene.types import Schema as GrapheneSchema
from graphql_relay import from_global_id, to_global_id

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

    def test_success_connection(self):
        schema = ProtectorSchema(
            query=Query,
        )
        self.assertIsInstance(schema, GrapheneSchema)
        result = schema.execute(
            """{ someNodes(first: 100) {
                edges { node { id } }
                pageInfo {
                    endCursor
                }
            } }"""
        )
        self.assertFalse(result.errors)
        self.assertEqual(len(result.data["someNodes"]["edges"]), 100)
        self.assertEqual(
            result.data["someNodes"]["edges"][99]["node"]["id"],
            to_global_id("SomeNode", "id-99"),
        )

        result = schema.execute(
            """{ someNodes(after: "%s", first: 100) {
                edges { node { id } }
            } }"""
            % result.data["someNodes"]["pageInfo"]["endCursor"]
        )
        self.assertFalse(result.errors)
        self.assertEqual(len(result.data["someNodes"]["edges"]), 100)
        self.assertEqual(
            from_global_id(
                result.data["someNodes"]["edges"][99]["node"]["id"]
            )[1],
            "id-199",
        )

    def test_error_connection(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=3, selections=None, complexity=None),
        )
        self.assertIsInstance(schema, GrapheneSchema)
        with self.subTest("success"):
            result = schema.execute(
                """{ someNodes(first: 100) {
                    edges { node { id } }
                    pageInfo {
                        endCursor
                    }
                } }"""
            )
            self.assertFalse(result.errors)
        with self.subTest("error"):
            result = schema.execute(
                """{ someNodes(first: 100) {
                    edges { node { id { hello } } }
                    pageInfo {
                        endCursor
                    }
                } }"""
            )
            self.assertTrue(result.errors)
