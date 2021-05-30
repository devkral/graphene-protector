import graphene

from graphene_protector import Limits, ProtectorBackend
from ..base import Person


class Query(graphene.ObjectType):

    person = graphene.Field(Person)
    person2 = graphene.Field(Person)

    def resolve_person(root, info):
        return Person(id=100, depth=10, age=34)

    def resolve_person2(root, info):
        return Person(id=200, depth=10, age=34)


schema = graphene.Schema(query=Query)

backend = ProtectorBackend(
    limits=Limits(depth=2, selections=None, complexity=None)
)
