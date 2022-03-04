from __future__ import annotations

from graphene_protector import Limits
from graphene_protector.django.strawberry import Schema as ProtectorSchema

import strawberry


@strawberry.type
class Person:
    id: strawberry.ID
    age: int
    depth: int

    @strawberry.field
    def child(self, info) -> Person:
        if self.depth == 0:
            return None
        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


@strawberry.type
class Query:
    @strawberry.field
    def person(root, info) -> Person:
        return Person(id=100, depth=10, age=34)

    @Limits(depth=4)
    @strawberry.field
    def person2(root, info) -> Person:
        return Person(id=200, depth=10, age=34)


schema = ProtectorSchema(query=Query)
