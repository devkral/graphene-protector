from . import base
from graphene.types import Schema as GrapheneSchema


class Schema(GrapheneSchema, base.SchemaMixin):
    def __init__(
        self,
        *args,
        limits=base.MISSING_LIMITS,
        path_ignore_pattern=base.default_path_ignore_pattern,
        **kwargs
    ):
        self.protector_default_limits = limits
        self.protector_path_ignore_pattern = path_ignore_pattern
        super().__init__(*args, **kwargs)
