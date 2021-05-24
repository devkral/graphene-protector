import graphene


class Person(graphene.ObjectType):
    id = graphene.ID()
    age = graphene.Int()
    depth = graphene.Int()
    child = graphene.Field(lambda: Person)

    def resolve_child(self, info):
        if self.depth == 0:
            return None
        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


class Query(graphene.ObjectType):

    person1 = graphene.Field(Person)
    person2 = graphene.Field(Person)

    def resolve_person1(root, info):
        return Person(id=100, depth=10, age=34)

    def resolve_person2(root, info):
        return Person(id=200, depth=20, age=34)


schema = graphene.Schema(query=Query)
query = """
    query something{
      person1 {
        id
        age
      }
    }
"""


def test_query():
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {"person": {"id": "1", "age": 27}}


if __name__ == "__main__":
    result = schema.execute(query)
    print(result.data["person"])
