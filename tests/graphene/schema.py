import graphene
from graphene import relay
from graphql_relay import from_global_id


class SomeNode(graphene.ObjectType):
    class Meta:
        interfaces = (relay.Node,)

    hello = graphene.String()

    def resolve_hello(root, info):
        return "World"

    @classmethod
    def get_node(cls, info, id):
        return SomeNode(id=id)


class SomeNodeConnection(relay.Connection):
    class Meta:
        node = SomeNode

    class Edge:
        pass


class Query(graphene.ObjectType):
    node = relay.Node.Field()

    hello = graphene.String()

    def resolve_hello(root, info):
        return "World"

    some_nodes = relay.ConnectionField(SomeNodeConnection)

    def resolve_some_nodes(root, info, **kwargs):
        return relay.ConnectionField.resolve_connection(
            SomeNodeConnection,
            kwargs,
            [SomeNode(id=f"id-{x}") for x in range(200)],
        )
