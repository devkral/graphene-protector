from graphql.type import (
    GraphQLField,
    GraphQLObjectType,
    GraphQLString,
)

try:
    field = GraphQLField(GraphQLString, resolve=lambda *_: "World")
except TypeError:
    field = GraphQLField(GraphQLString, resolver=lambda *_: "World")

Query = GraphQLObjectType(
    "Query",
    lambda: {"hello": field},
)
