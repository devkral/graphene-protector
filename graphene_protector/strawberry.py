from strawberry import Schema as StrawberrySchema
from strawberry.extensions import AddValidationRules

from . import base


class CustomGrapheneProtector(AddValidationRules):
    """
    Add a validator to limit the used resources

    Example:

    >>> import strawberry
    >>> from graphene_protector.strawberry import CustomGrapheneProtector
    >>> from graphene_protector import Limits
    >>>
    >>> schema = strawberry.Schema(
    ...     Query,
    ...     extensions=[
    ...         CustomGrapheneProtector(limits=Limits())
    ...     ]
    ... )

    Arguments:

    `limits: Limits`
        The limits definition
    """

    def __init__(self, limits: base.Limits = None):
        if limits:

            class CustomLimitsValidationRule(base.LimitsValidationRule):
                default_limits = limits

        else:
            CustomLimitsValidationRule = base.LimitsValidationRule

        super().__init__([CustomLimitsValidationRule])


class Schema(base.SchemaMixin, StrawberrySchema):
    def __init__(self, *args, limits=base.Limits(), **kwargs):
        self.default_limits = limits
        super().__init__(*args, **kwargs)
        for extension in self.extensions:
            if isinstance(extension, CustomGrapheneProtector):
                # undecorate if CustomGrapheneProtector is in extensions
                if hasattr(self, "execute"):
                    self.execute = self.execute.__wrapped__
                if hasattr(self, "execute_async"):
                    self.execute_async = self.execute_async.__wrapped__
                if hasattr(self, "subscribe"):
                    self.subscribe = self.subscribe.__wrapped__
                break
