from graphene.types import Schema as GrapheneSchema

from . import base


class Schema(base.SchemaMixin, GrapheneSchema):
    def __init__(
        self,
        *args,
        limits=base.MISSING_LIMITS,
        path_ignore_pattern=base.default_path_ignore_pattern,
        auto_camelcase=True,
        **kwargs
    ):
        self.protector_default_limits = limits
        self.protector_path_ignore_pattern = path_ignore_pattern
        self.auto_camelcase = auto_camelcase
        super().__init__(*args, auto_camelcase=auto_camelcase, **kwargs)

    def get_protector_auto_snakecase(self):
        return self.auto_camelcase
