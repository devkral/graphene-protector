from django.conf import settings

import graphene

from . import base


def _get_default_limit_from_settings(name):
    if hasattr(settings, name):
        return getattr(settings, name)
    return base.MISSING


class ProtectorBackend(base.ProtectorBackend):
    def get_default_limits(self):
        return base.merge_limits(
            base.merge_limits(
                base.DEFAULT_LIMITS,
                base.Limits(
                    depth=_get_default_limit_from_settings(
                        "GRAPHENE_PROTECTOR_DEPTH_LIMIT"
                    ),
                    selections=_get_default_limit_from_settings(
                        "GRAPHENE_PROTECTOR_SELECTIONS_LIMIT"
                    ),
                    complexity=_get_default_limit_from_settings(
                        "GRAPHENE_PROTECTOR_COMPLEXITY_LIMIT"
                    ),
                ),
            ),
            self.default_limits,
        )


class Schema(graphene.Schema):
    def __init__(self, *args, **kwargs):
        self.backend = kwargs.pop("backend", ProtectorBackend())
        super().__init__(*args, **kwargs)

    def execute(self, *args, **kwargs):
        kwargs.setdefault("backend", self.backend)
        return super().execute(*args, **kwargs)
