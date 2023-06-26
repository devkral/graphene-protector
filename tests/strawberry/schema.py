from typing import List, Optional, Union

import strawberry
from strawberry.types import Info


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
class Query:
    @strawberry.field
    def persons(
        self, info: Info, filters: Optional[List[PersonFilter]] = None
    ) -> List[Union[Person1, Person2]]:
        return [
            Person1(name="Hans", child=Person2(name="Willi")),
            Person2(name="Zoe", child=Person1(name="Hubert")),
        ]

    @strawberry.field
    def in_out(self, into: List[str]) -> List[str]:
        return into
