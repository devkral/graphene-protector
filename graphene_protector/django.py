from django.conf import settings

import graphene

from . import base


def _get_default_from_settings(name, default):
    if hasattr(settings, name):
        return getattr(settings, name)
    return default


class ProtectorBackend(base.ProtectorBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _limits_for_missing(self, name):
        if name == "depth":
            return _get_default_from_settings(
                "GRAPHENE_PROTECTOR_DEPTH_LIMIT", 20
            )
        elif name == "selections":
            return _get_default_from_settings(
                "GRAPHENE_PROTECTOR_SELECTIONS_LIMIT", None
            )
        elif name == "complexity":
            return _get_default_from_settings(
                "GRAPHENE_PROTECTOR_COMPLEXITY_LIMIT", 100
            )


class Schema(graphene.Schema):
    def __init__(self, *args, **kwargs):
        self.backend = kwargs.pop("backend", ProtectorBackend())
        super().__init__(*args, **kwargs)

    def execute(self, *args, **kwargs):
        kwargs.setdefault("backend", self.backend)
        return super().execute(*args, **kwargs)
