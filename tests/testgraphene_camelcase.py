__package__ = "tests"

import unittest
import graphene

from graphene_protector import Limits
from graphene_protector.graphene import Schema as ProtectorSchema


class Person(graphene.ObjectType):
    id = graphene.ID()
    age = graphene.Int()
    depth = graphene.Int()
    child_a = graphene.Field(lambda: Person)

    def resolve_child_a(self, info):
        if self.depth == 0:
            return None
        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


class Person3(graphene.ObjectType):
    id = graphene.ID()
    age = graphene.Int()
    depth = graphene.Int()
    child_a = Limits(depth=None)(graphene.Field(Person))

    def resolve_child_a(self, info):
        if self.depth == 0:
            return None

        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


class Query(graphene.ObjectType):

    set_directly = Limits(depth=2)(graphene.Field(Person))
    unset_directly = Limits(depth=None)(graphene.Field(Person))
    unset_hierachy = Limits(depth=1)(graphene.Field(Person3))

    def resolve_set_directly(root, info):
        return Person(id=100, depth=10, age=34)

    def resolve_unset_directly(root, info):
        return Person(id=200, depth=10, age=34)

    def resolve_unset_hierachy(root, info):
        return Person3(id=300, depth=10, age=34)


schema = ProtectorSchema(
    query=Query,
    auto_camelcase=True,
    limits=Limits(depth=3, selections=None, complexity=None),
)


class TestField(unittest.TestCase):
    def test_set_directly(self):
        with self.subTest("success"):
            query = """
    query something{
      setDirectly {
        childA {
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
        childA {
            childA {
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
        childA {
            childA {
                childA {
                    childA {
                        childA {
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
        childA {
            childA {
                childA {
                    childA {
                        childA {
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
