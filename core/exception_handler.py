"""Global DRF exception handling with unified response formatting."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.constants import (
    DEFAULT_ERROR_MESSAGE,
    ERROR_CODE_AUTHENTICATION_FAILED,
    ERROR_CODE_METHOD_NOT_ALLOWED,
    ERROR_CODE_NOT_AUTHENTICATED,
    ERROR_CODE_NOT_FOUND,
    ERROR_CODE_PARSE_ERROR,
    ERROR_CODE_PERMISSION_DENIED,
    ERROR_CODE_SERVER_ERROR,
    ERROR_CODE_THROTTLED,
    ERROR_CODE_VALIDATION,
    REQUEST_ID_META_KEY,
)
from core.exceptions import ApplicationError

logger = logging.getLogger("mess_track.exceptions")

EXCEPTION_CODE_MAP: dict[type[Exception], str] = {
    ValidationError: ERROR_CODE_VALIDATION,
    AuthenticationFailed: ERROR_CODE_AUTHENTICATION_FAILED,
    NotAuthenticated: ERROR_CODE_NOT_AUTHENTICATED,
    PermissionDenied: ERROR_CODE_PERMISSION_DENIED,
    DjangoPermissionDenied: ERROR_CODE_PERMISSION_DENIED,
    NotFound: ERROR_CODE_NOT_FOUND,
    ParseError: ERROR_CODE_PARSE_ERROR,
    MethodNotAllowed: ERROR_CODE_METHOD_NOT_ALLOWED,
    Throttled: ERROR_CODE_THROTTLED,
}


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Return a unified error payload for handled and unhandled exceptions."""

    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)
    meta = {REQUEST_ID_META_KEY: request_id} if request_id else {}

    if response is None:
        logger.exception(
            "Unhandled exception during request processing",
            extra={"request_id": request_id, "path": getattr(request, "path", None)},
        )
        return Response(
            {
                "success": False,
                "message": DEFAULT_ERROR_MESSAGE,
                "code": ERROR_CODE_SERVER_ERROR,
                "errors": {},
                "meta": meta,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = _resolve_error_code(exc)
    message = _resolve_message(exc, response)
    errors = _resolve_errors(exc, response)
    response.data = {
        "success": False,
        "message": message,
        "code": code,
        "errors": errors,
        "meta": _merge_meta(meta, getattr(exc, "meta", None)),
    }
    return response


def _resolve_error_code(exc: Exception) -> str:
    if isinstance(exc, ApplicationError):
        return str(exc.get_codes())

    for exception_class, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exception_class):
            return code

    return ERROR_CODE_SERVER_ERROR


def _resolve_message(exc: Exception, response: Response) -> str:
    if isinstance(exc, ValidationError):
        return "Validation failed"
    if isinstance(exc, Throttled):
        return "Request was throttled"
    if isinstance(response.data, Mapping) and isinstance(
        response.data.get("detail"), str
    ):
        return response.data["detail"]
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str):
        return detail
    return DEFAULT_ERROR_MESSAGE


def _resolve_errors(exc: Exception, response: Response) -> Any:
    if isinstance(exc, ApplicationError):
        return exc.errors
    if isinstance(exc, ValidationError):
        return response.data
    if isinstance(response.data, Mapping) and "detail" in response.data:
        return {}
    return response.data if response.data is not None else {}


def _merge_meta(
    base_meta: dict[str, Any], extra_meta: dict[str, Any] | None
) -> dict[str, Any]:
    merged = dict(base_meta)
    if extra_meta:
        merged.update(extra_meta)
    return merged
