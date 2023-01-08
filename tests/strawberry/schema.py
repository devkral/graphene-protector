from typing import List, Optional
import strawberry
from strawberry.types import Info


@strawberry.input
class PersonFilter:
    name: str


@strawberry.type
class Person:
    name: str


@strawberry.type
class Query:
    @strawberry.field
    def persons(
        self, info: Info, filters: Optional[List[PersonFilter]] = None
    ) -> List[Person]:
        return [
            Person(name="Hans"),
            Person(name="Zoe"),
        ]

    @strawberry.field
    def in_out(self, into: List[str]) -> List[str]:
        return into
