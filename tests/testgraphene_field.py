__package__ = "tests"

import unittest

import graphene

from graphene_protector import Limits
from graphene_protector.graphene import Schema as ProtectorSchema

from .graphene_base import Person


class Person3(graphene.ObjectType):
    id = graphene.ID()
    age = graphene.Int()
    depth = graphene.Int()
    child = Limits(depth=None)(graphene.Field(Person))

    def resolve_child(self, info):
        if self.depth == 0:
            return None

        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


class Person4(graphene.ObjectType):
    id = graphene.ID()
    age = graphene.Int()
    depth = graphene.Int()
    child = Limits(depth=2)(graphene.Field(Person))
    child2 = Limits(depth=2, passthrough={"depth"})(graphene.Field(Person))

    def resolve_child(self, info):
        if self.depth == 0:
            return None

        return Person(id=self.id + 1, depth=self.depth - 1, age=34)

    def resolve_child2(self, info):
        if self.depth == 0:
            return None

        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


class Query(graphene.ObjectType):
    setDirectly = Limits(depth=2)(graphene.Field(Person))
    unsetDirectly = Limits(depth=None)(graphene.Field(Person))
    unsetHierachy = Limits(depth=1)(graphene.Field(Person3))
    setHierachy = Limits(depth=1)(graphene.Field(Person4))

    def resolve_setDirectly(root, info):
        return Person(id=100, depth=10, age=34)

    def resolve_unsetDirectly(root, info):
        return Person(id=200, depth=10, age=34)

    def resolve_unsetHierachy(root, info):
        return Person3(id=300, depth=10, age=34)

    def resolve_setHierachy(root, info):
        return Person4(id=400, depth=10, age=34)


schema = ProtectorSchema(
    query=Query, limits=Limits(depth=3, selections=None, complexity=None, gas=None)
)


class TestField(unittest.TestCase):
    def test_set_directly(self):
        with self.subTest("success"):
            query = """
    query something{
      setDirectly {
        child {
            age
        }
      }
    }
"""
            result = schema.execute(query)
            self.assertFalse(result.errors)

        with self.subTest("rejected"):
            query = """
    query something{
      setDirectly {
        child {
            child {
                age
            }
        }
      }
    }
"""
            result = schema.execute(query)
            self.assertTrue(result.errors)

    def test_unset_directly(self):
        query = """
    query something{
      unsetDirectly {
        child {
            child {
                child {
                    child {
                        child {
                            age
                        }
                    }
                }
            }
        }
      }
    }
"""
        result = schema.execute(query)
        self.assertFalse(result.errors)

    def test_unset_hierachy(self):
        query = """
    query something{
      unsetHierachy {
        child {
            child {
                child {
                    child {
                        child {
                            age
                        }
                    }
                }
            }
        }
      }
    }
"""
        result = schema.execute(query)
        self.assertFalse(result.errors)

    def test_set_hierachy(self):
        with self.subTest("success"):
            query = """
    query something{
      setHierachy{
        child {
            child {
                age
            }
        }
      }
    }
"""
            result = schema.execute(query)
            self.assertFalse(result.errors)

        with self.subTest("rejected"):
            query = """
    query something{
      setHierachy {
        child {
            child {
                child {
                    age
                }
            }
        }
      }
    }
"""
            result = schema.execute(query)
            self.assertTrue(result.errors)
            # test passthrough
            query = """
    query something{
      setHierachy{
        child {
            child2 {
                age
            }
        }
      }
    }
"""
            result = schema.execute(query)
            self.assertTrue(result.errors)
