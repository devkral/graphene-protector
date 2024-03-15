from typing import Iterable, List, Optional, Union

import strawberry
from strawberry.types import Info

from graphene_protector import gas_usage


@strawberry.input
class PersonFilter:
    name: str


@strawberry.type
class Person1:
    name: str
    child: Optional[Union["Person1", "Person2"]] = None


@strawberry.type
class Person2:
    name: str
    child: Optional[Union["Person1", "Person2"]] = None


@strawberry.type
class SomeNode(strawberry.relay.Node):
    myid: strawberry.relay.NodeID[str]

    @classmethod
    def resolve_nodes(
        cls,
        *,
        info: Info,
        node_ids: Iterable[str],
        required: bool,
    ):
        return map(lambda id: SomeNode(myid=id), node_ids)


@strawberry.type
class Query:
    # should work, but broken upstream
    # node: strawberry.relay.Node = strawberry.relay.node()
    @strawberry.field()
    @staticmethod
    def node(info, id: strawberry.relay.GlobalID) -> Optional[strawberry.relay.Node]:
        return id.resolve_node(info=info, required=False)

    @strawberry.field
    def persons(
        self, info: Info, filters: Optional[List[PersonFilter]] = None
    ) -> List[Union[Person1, Person2]]:
        return [
            Person1(name="Hans", child=Person2(name="Willi")),
            Person2(name="Zoe", child=Person1(name="Hubert")),
        ]

    @gas_usage(lambda **_kwargs: 4)
    @strawberry.field
    def in_out(self, into: List[str]) -> List[str]:
        return into

    @strawberry.relay.connection(strawberry.relay.ListConnection[SomeNode])
    def some_nodes(self) -> list[SomeNode]:
        return [SomeNode(myid=f"id-{x}") for x in range(200)]
