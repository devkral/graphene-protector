from graphql.type import (
    GraphQLField,
    GraphQLObjectType,
    GraphQLString,
)

from graphene_protector import gas_usage

try:
    field = GraphQLField(GraphQLString, resolve=lambda *_: "World")
except TypeError:
    field = GraphQLField(GraphQLString, resolver=lambda *_: "World")

Query = GraphQLObjectType(
    "Query",
    lambda: {"hello": gas_usage(1)(field)},
)
