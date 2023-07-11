from typing import Iterable, Optional

import strawberry
from strawberry import relay

from graphene_protector import Limits
from graphene_protector.django.strawberry import Schema as ProtectorSchema


@strawberry.type
class Person(relay.Node):
    id: relay.NodeID[strawberry.ID]
    age: int
    depth: int

    @strawberry.field
    def child(self, info) -> "Person":
        if self.depth == 0:
            return None
        return Person(id=self.id + 1, depth=self.depth - 1, age=34)

    @Limits(depth=1)
    @strawberry.field
    def child_limited(self, info) -> "Person":
        if self.depth == 0:
            return None
        return Person(id=self.id + 1, depth=self.depth - 1, age=34)


@strawberry.type
class Query:
    # should work, but broken upstream
    # node: strawberry.relay.Node = strawberry.relay.node()
    @strawberry.field()
    @staticmethod
    def node(
        info, id: strawberry.relay.GlobalID
    ) -> Optional[strawberry.relay.Node]:
        return id.resolve_node(info=info, required=False)

    @strawberry.field
    def person(root, info) -> Person:
        return Person(id=100, depth=10, age=34)

    @Limits(depth=4)
    @strawberry.field
    def person2(root, info) -> Person:
        return Person(id=200, depth=10, age=34)

    @Limits(depth=3)
    @relay.connection(relay.ListConnection[Person])
    def persons(self) -> Iterable[Person]:
        return [Person(id=200, depth=10, age=34) for i in range(2000)]


schema = ProtectorSchema(query=Query)
