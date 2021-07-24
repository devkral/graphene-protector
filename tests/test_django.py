from django.test import TestCase
from django.conf import settings

from graphene_django.settings import graphene_settings

from graphene_protector import Limits
from graphene_protector.django import ProtectorBackend

from graphql import print_schema
from unittest.mock import patch


backend = ProtectorBackend(limits=Limits(selections=100))


class TestDjango(TestCase):
    def test_defaults(self):
        limits = backend.get_default_limits()
        self.assertEqual(settings.GRAPHENE_PROTECTOR_DEPTH_LIMIT, limits.depth)
        self.assertNotEqual(
            settings.GRAPHENE_PROTECTOR_SELECTIONS_LIMIT, limits.selections
        )

    def test_field_overwrites(self):
        schema = graphene_settings.SCHEMA

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
            result = schema.execute(query, backend=backend)
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
            result = schema.execute(query, backend=backend)
            self.assertFalse(result.errors)

    @patch("graphene_protector.base.check_resource_usage")
    def test_generate_scheme(self, mock):
        graphene_settings.SCHEMA.introspect()
        self.assertFalse(mock.called)
        print_schema(graphene_settings.SCHEMA)
        self.assertFalse(mock.called)
