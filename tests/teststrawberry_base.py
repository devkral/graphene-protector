__package__ = "tests"

import unittest

#
from strawberry import Schema as StrawberrySchema
from strawberry.relay import from_base64, to_base64

from graphene_protector import Limits, SchemaMixin
from graphene_protector.strawberry import CustomGrapheneProtector
from graphene_protector.strawberry import Schema as ProtectorSchema

from .strawberry.schema import Query


class CustomSchema(SchemaMixin, StrawberrySchema):
    protector_default_limits = Limits(
        depth=2, selections=None, complexity=None, gas=None
    )


class CustomSchemaWithoutOperationWrapping(
    SchemaMixin, StrawberrySchema, protector_per_operation_validation=False
):
    protector_default_limits = Limits(
        depth=2, selections=None, complexity=None, gas=None
    )


class TestStrawberry(unittest.IsolatedAsyncioTestCase):
    def test_simple_sync(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None, gas=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        self.assertTrue(
            any(
                filter(
                    lambda x: isinstance(x, CustomGrapheneProtector),
                    schema.extensions,
                )
            )
        )
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

    def test_failing_sync(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=1, selections=None, complexity=None, gas=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        self.assertTrue(
            any(
                filter(
                    lambda x: isinstance(x, CustomGrapheneProtector),
                    schema.extensions,
                )
            )
        )
        result = schema.execute_sync(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {child{
                        ...on Person1 {
                            name
                        }
                    }}
            } }"""
        )
        self.assertTrue(result.errors)

    async def test_failing_async(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=1, selections=None, complexity=None, gas=None),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        self.assertTrue(
            any(
                filter(
                    lambda x: isinstance(x, CustomGrapheneProtector),
                    schema.extensions,
                )
            )
        )
        result = await schema.execute(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {child{
                        ...on Person1 {
                            name
                        }
                    }}
            } }"""
        )
        self.assertTrue(result.errors)

    def test_in_out(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None, gas=4),
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = schema.execute_sync('{ inOut(into: ["a", "b"]) }')
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"inOut": ["a", "b"]})
        result = schema.execute_sync("{ inOut(into: []), inOut2: inOut(into: []) }")
        self.assertTrue(result.errors)

    async def test_simple_async(self):
        schema = ProtectorSchema(
            query=Query,
            limits=Limits(depth=2, selections=None, complexity=None, gas=None),
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
        schema = CustomSchemaWithoutOperationWrapping(
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

    async def test_failing_async_custom(self):
        schema = CustomSchemaWithoutOperationWrapping(
            query=Query,
            extensions=[
                CustomGrapheneProtector(
                    limits=Limits(depth=2, selections=None, complexity=None, gas=None),
                )
            ],
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {child{
                        ...on Person1 {
                            name
                        }
                    }}
            } }"""
        )
        self.assertTrue(result.errors)

    async def test_success_ignoring_async(self):
        schema = ProtectorSchema(
            query=Query,
            path_ignore_pattern=r"child",
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute(
            """{ persons(filters: [{name: "Hans"}]) {
                ... on Person1 {name}
                ... on Person2 {child{
                        ...on Person1 {
                            name
                        }
                    }}
            } }"""
        )
        self.assertFalse(result.errors)

    async def test_success_node_async(self):
        schema = ProtectorSchema(
            query=Query,
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute(
            """{ node (id: "%s") {
                id
            } }"""
            % (to_base64("SomeNode", "foo"))
        )
        self.assertFalse(result.errors)
        self.assertEqual(result.data["node"]["id"], to_base64("SomeNode", "foo"))

    async def test_success_connection_async(self):
        schema = ProtectorSchema(
            query=Query,
        )
        self.assertIsInstance(schema, StrawberrySchema)
        result = await schema.execute(
            """{ someNodes {
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
            to_base64("SomeNode", "id-99"),
        )

        result = await schema.execute(
            """{ someNodes(after: "%s") {
                edges { node { id } }
            } }"""
            % result.data["someNodes"]["pageInfo"]["endCursor"]
        )
        self.assertFalse(result.errors)
        self.assertEqual(len(result.data["someNodes"]["edges"]), 100)
        self.assertEqual(
            from_base64(result.data["someNodes"]["edges"][99]["node"]["id"])[1],
            "id-199",
        )
