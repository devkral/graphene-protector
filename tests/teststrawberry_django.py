from django.conf import settings
from django.test import TestCase
from graphql import print_schema

from graphene_protector import Limits
from graphene_protector.django.strawberry import (
    Schema as ProtectorGrapheneSchema,
)

from .django.schema_strawberry import Query as QueryNonPlus
from .django.schema_strawberry_plus import Query as QueryPlus

schema_nonplus = ProtectorGrapheneSchema(
    query=QueryNonPlus, limits=Limits(selections=100)
)

schema_plus = ProtectorGrapheneSchema(
    query=QueryPlus, limits=Limits(selections=100)
)


class TestDjangoStrawberry(TestCase):
    def test_defaults(self):
        for index, schema in enumerate([schema_nonplus, schema_plus]):
            with self.subTest(index):
                limits = schema.get_protector_default_limits()
                self.assertEqual(
                    settings.GRAPHENE_PROTECTOR_DEPTH_LIMIT, limits.depth
                )
                self.assertNotEqual(
                    settings.GRAPHENE_PROTECTOR_SELECTIONS_LIMIT,
                    limits.selections,
                )

    def test_relay_path_ignore(self):
        for index, schema in enumerate([schema_nonplus, schema_plus]):
            with self.subTest(f"rejected: {index}"):
                query = """
            query something{
            persons {
                edges {
                    node {
                        child {
                            id
                        }
                    }
                }
            }
            }
        """
                result = schema.execute_sync(query)
                self.assertTrue(result.errors)

            with self.subTest(f"success: {index}"):
                query = """
            query something{
            persons {
                edges {
                    node {
                        id
                    }
                }
            }
            }
        """
                result = schema.execute_sync(query)
                self.assertFalse(result.errors)

    def test_field_overwrites(self):
        for index, schema in enumerate([schema_nonplus, schema_plus]):
            with self.subTest(f"rejected: {index}"):
                query = """
        query something{
        person {
            id
            age
            child {
                child {
                    age
                }
            }
        }
        }
    """
                result = schema.execute_sync(query)
                self.assertTrue(result.errors)

            with self.subTest(f"success: {index}"):
                query = """
        query something{
        person2 {
            id
            age
            child {
                child {
                    age
                }
            }
        }
        }
    """
                result = schema.execute_sync(query)
                self.assertFalse(result.errors)

    def test_field_overwrites_circular_and_snake_case_converting(self):
        for index, schema in enumerate([schema_nonplus, schema_plus]):
            with self.subTest(f"rejected: {index}"):
                query = """
        query something{
        person2 {
            id
            age
            childLimited {
                childLimited {
                    age
                }
            }
        }
        }
    """
                result = schema.execute_sync(query)
                self.assertTrue(result.errors)

            with self.subTest(f"success: {index}"):
                query = """
        query something{
        person2 {
            id
            age
            childLimited {
                age
            }
        }
        }
    """
                result = schema.execute_sync(query)
                self.assertFalse(result.errors)

    def test_generate_scheme(self):
        for index, schema in enumerate([schema_nonplus, schema_plus]):
            with self.subTest(index):
                schema.introspect()
                print_schema(getattr(schema, "_schema", schema))
                # doesn't work
                # print_schema(schema)
