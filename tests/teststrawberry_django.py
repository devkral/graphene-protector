from django.test import TestCase
from django.conf import settings

from graphene_protector import Limits
from graphene_protector.django.strawberry import (
    Schema as ProtectorGrapheneSchema,
)

from graphql import print_schema

from .django.schema_strawberry import Query

schema = ProtectorGrapheneSchema(query=Query, limits=Limits(selections=100))


class TestDjangoStrawberry(TestCase):
    def test_defaults(self):
        limits = schema.get_default_limits()
        self.assertEqual(settings.GRAPHENE_PROTECTOR_DEPTH_LIMIT, limits.depth)
        self.assertNotEqual(
            settings.GRAPHENE_PROTECTOR_SELECTIONS_LIMIT, limits.selections
        )

    def test_field_overwrites(self):

        with self.subTest("rejected"):
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

        with self.subTest("success"):
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

        with self.subTest("rejected"):
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

        with self.subTest("success"):
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
        schema.introspect()
        print_schema(getattr(schema, "_schema", schema))
        # doesn't work
        # print_schema(schema)
