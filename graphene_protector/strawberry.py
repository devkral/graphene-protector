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
        auto_snakecase: Optional[bool] = None,
        camelcase_path: Optional[bool] = None,
    ):
        # if there is a custom option, create a subclass
        if (
            limits is not None
            or path_ignore_pattern is not None
            or full_validation is not None
            or auto_snakecase is not None
            or camelcase_path is not None
        ):
            _locals = locals()

            class CustomLimitsValidationRule(base.LimitsValidationRule):
                default_limits = limits
                path_ignore_pattern = _locals["path_ignore_pattern"]
                full_validation = _locals["full_validation"]
                auto_snakecase = _locals["auto_snakecase"]
                camelcase_path = _locals["camelcase_path"]

        else:
            CustomLimitsValidationRule = base.LimitsValidationRule

        super().__init__([CustomLimitsValidationRule])


class Schema(
    base.SchemaMixin,
    StrawberrySchema,
    protector_per_operation_validation=False,
):
    def __init__(
        self,
        *args,
        limits=base.MISSING_LIMITS,
        path_ignore_pattern=base.default_path_ignore_pattern,
        extensions=(),
        **kwargs
    ):
        self.protector_default_limits = limits
        self.protector_path_ignore_pattern = path_ignore_pattern
        for extension in extensions:
            if isinstance(extension, CustomGrapheneProtector):
                break
        else:
            extensions = (CustomGrapheneProtector(), *extensions)

        super().__init__(*args, extensions=extensions, **kwargs)

    def get_protector_auto_snakecase(self):
        return self.config.name_converter.auto_camel_case
