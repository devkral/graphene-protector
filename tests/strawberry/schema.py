import strawberry
from strawberry.types import Info


@strawberry.type
class Query:
    @strawberry.field
    def hello(self, info: Info) -> str:
        return "World"
