__package__ = "tests"

import unittest
import graphene
from graphene_protector import Limits, ProtectorBackend

from .base import Person


class Query(graphene.ObjectType):

    person = graphene.Field(Person)

    def resolve_person(root, info):
        return Person(id=100, depth=10, age=34)


class TestGlobal(unittest.TestCase):
    def test_defaults(self):
        backend = ProtectorBackend()
        for lname in ["depth", "selections", "complexity"]:
            with self.subTest(f"Test default: {lname}"):
                limit = backend.default_for_missing_limit(lname)
                self.assertTrue(limit is None or limit >= 0)

    def test_depth(self):
        backend = ProtectorBackend(limits=Limits(depth=2))
        schema = graphene.Schema(query=Query)

        with self.subTest("success"):
            query = """
    query something{
      person {
        id
        age
        child {
            age
        }
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertFalse(result.errors)
            self.assertDictEqual(
                result.data,
                {"person": {"id": "100", "age": 34, "child": {"age": 34}}},
            )

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

    def test_selections(self):
        with self.subTest("success"):
            pass

        with self.subTest("rejected"):
            pass

    def test_complexity(self):
        with self.subTest("success"):
            pass

        with self.subTest("rejected"):
            pass
