from . import base
from graphene.types import Schema as GrapheneSchema


class Schema(GrapheneSchema, base.SchemaMixin):
    def __init__(self, *args, limits=base.Limits(), **kwargs):
        self.default_limits = limits
        super().__init__(*args, **kwargs)
