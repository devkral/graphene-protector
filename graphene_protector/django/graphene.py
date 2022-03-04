from .. import graphene
from . import base


class Schema(base.GetDefaultsMixin, graphene.Schema):
    pass
