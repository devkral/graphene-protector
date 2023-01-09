from typing import List, Optional, Union
import strawberry
from strawberry.types import Info


@strawberry.input
class PersonFilter:
    name: str


@strawberry.type
class Person1:
    name: str


@strawberry.type
class Person2:
    name: str


@strawberry.type
class Query:
    @strawberry.field
    def persons(
        self, info: Info, filters: Optional[List[PersonFilter]] = None
    ) -> List[Union[Person1, Person2]]:
        return [
            Person1(name="Hans"),
            Person2(name="Zoe"),
        ]

    @strawberry.field
    def in_out(self, into: List[str]) -> List[str]:
        return into
