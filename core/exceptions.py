"""Custom exception primitives for API responses."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException

from core.constants import DEFAULT_ERROR_MESSAGE, ERROR_CODE_SERVER_ERROR


class ApplicationError(APIException):
    """Base API exception that carries structured error payload details."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = DEFAULT_ERROR_MESSAGE
    default_code = ERROR_CODE_SERVER_ERROR

    def __init__(
        self,
        detail: Any = None,
        *,
        code: str | None = None,
        errors: Any = None,
        meta: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        self.errors = {} if errors is None else errors
        self.meta = {} if meta is None else meta
        super().__init__(
            detail=detail if detail is not None else self.default_detail,
            code=code or self.default_code,
        )
