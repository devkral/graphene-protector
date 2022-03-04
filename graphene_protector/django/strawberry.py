from .. import strawberry

from . import base


class Schema(base.GetDefaultsMixin, strawberry.Schema):
    pass
