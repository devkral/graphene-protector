__package__ = "tests"

import unittest
import graphene
from dataclasses import fields

from graphene_protector import Limits, ProtectorBackend
from .base import Person


class Query(graphene.ObjectType):

    person = graphene.Field(Person)
    person2 = graphene.Field(Person)

    def resolve_person(root, info):
        return Person(id=100, depth=10, age=34)

    def resolve_person2(root, info):
        return Person(id=200, depth=10, age=34)


schema = graphene.Schema(query=Query)


class TestGlobal(unittest.TestCase):
    def test_defaults(self):
        backend = ProtectorBackend()
        dlimit = backend.get_default_limits()
        for field in fields(dlimit):
            with self.subTest(f"Test default: {field.name}"):
                limit = getattr(dlimit, field.name)
                self.assertTrue(limit is None or limit >= 0)

    def test_depth(self):
        backend = ProtectorBackend(
            limits=Limits(depth=2, selections=None, complexity=None)
        )

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
        backend = ProtectorBackend(
            limits=Limits(selections=2, depth=None, complexity=None)
        )
        with self.subTest("success 1"):
            query = """
    query something{
      person {
        id
        child {
            id
        }
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertFalse(result.errors)
        with self.subTest("success 2"):
            query = """
    query something{
      person {
        id
      }
      person2 {
        id
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertFalse(result.errors)

        with self.subTest("rejected 1"):
            query = """
    query something{
      person {
        id
        age
        child {
            id
        }
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertTrue(result.errors)
        with self.subTest("rejected 2"):
            query = """
    query something{
      person {
        id
        child {
            id
            age
        }
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertTrue(result.errors)
        with self.subTest("rejected 3"):
            query = """
    query something{
      person {
        id
        age
      }
      person2 {
        id
        age
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertTrue(result.errors)

    def test_complexity(self):
        backend = ProtectorBackend(
            limits=Limits(selections=None, depth=None, complexity=2)
        )
        with self.subTest("success 1"):
            query = """
    query something{
      person {
        id
        age
      }
      person2 {
        id
        age
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertFalse(result.errors)
        with self.subTest("success 2"):
            query = """
    query something{
      person {
          child {
              id
          }
      }
      person2 {
          child {
              age
          }
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertFalse(result.errors)

        with self.subTest("rejected 1"):
            query = """
    query something{
      person {
          child {
              id
              age
          }
      }
    }
"""
            result = schema.execute(query, backend=backend)
            self.assertTrue(result.errors)

        with self.subTest("rejected 2"):
            query = """
    query something{
      person {
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
