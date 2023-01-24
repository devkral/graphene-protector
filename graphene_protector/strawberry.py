from typing import Optional
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

    def __init__(
        self,
        limits: Optional[base.Limits] = None,
        path_ignore_pattern: Optional[str] = None,
        full_validation: Optional[bool] = None,
    ):
        if (
            limits is not None
            or path_ignore_pattern is not None
            or full_validation is not None
        ):
            _path_ignore_pattern = path_ignore_pattern
            _full_validation = full_validation

            class CustomLimitsValidationRule(base.LimitsValidationRule):
                default_limits = limits
                path_ignore_pattern = _path_ignore_pattern
                full_validation = _full_validation

        else:
            CustomLimitsValidationRule = base.LimitsValidationRule

        super().__init__([CustomLimitsValidationRule])


class Schema(base.SchemaMixin, StrawberrySchema):
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
        for extension in self.extensions:
            if isinstance(extension, CustomGrapheneProtector):
                # undecorate if CustomGrapheneProtector is in extensions
                # TODO: preserve nonProtector decorators
                if hasattr(self, "execute"):
                    self.execute = self.execute.__wrapped__
                if hasattr(self, "execute_async"):
                    self.execute_async = self.execute_async.__wrapped__
                if hasattr(self, "subscribe"):
                    self.subscribe = self.subscribe.__wrapped__
                break
