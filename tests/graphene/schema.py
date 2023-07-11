import graphene
from graphene import relay
from graphql_relay import from_global_id


class SomeNode(graphene.ObjectType):
    class Meta:
        interfaces = (relay.Node,)

    @classmethod
    def get_node(cls, info, id):
        return SomeNode(id=id)


class Query(graphene.ObjectType):
    node = relay.Node.Field()

    hello = graphene.String()

    def resolve_hello(root, info):
        return "World"
