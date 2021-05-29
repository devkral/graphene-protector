import graphene
from graphene_protector import Limits, ProtectorBackend


class Person(graphene.ObjectType):
    id = graphene.ID()
    age = graphene.Int()
    depth = graphene.Int()
    child = graphene.Field(lambda: Person)

    def resolve_child(self, info):
        if self.depth == 0:
            return None
        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


class Query2(graphene.ObjectType):

    person1 = Limits()(graphene.Field(Person))
    person2 = graphene.Field(Person)

    def resolve_person1(root, info):
        return Person(id=100, depth=10, age=34)

    def resolve_person2(root, info):
        return Person(id=200, depth=10, age=34)


backend = ProtectorBackend()
schema = graphene.Schema(query=Query2)
query = """
    query something{
      person1 {
        id
        age
        child {
            child {
                age
            }
        }
      }
      person2 {
        id
      }
    }
"""


def test_query():
    result = schema.execute(query, backend=backend)
    assert not result.errors
    # assert result.data == {"person1": {"id": "1", "age": 27}}


if __name__ == "__main__":
    result = schema.execute(query, backend=backend)
    print(result)
    print(result.data["person1"])
