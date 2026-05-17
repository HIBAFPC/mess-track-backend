"""Reusable response helpers for consistent API responses."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response

from core.constants import DEFAULT_ERROR_MESSAGE, DEFAULT_SUCCESS_MESSAGE


def success_response(
    *,
    data: Any = None,
    message: str = DEFAULT_SUCCESS_MESSAGE,
    meta: dict[str, Any] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Return a standardized success response."""

    payload = {
        "success": True,
        "message": message,
        "data": {} if data is None else data,
        "meta": meta or {},
    }
    return Response(payload, status=status_code)


def error_response(
    *,
    message: str = DEFAULT_ERROR_MESSAGE,
    code: str,
    errors: Any = None,
    meta: dict[str, Any] | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Return a standardized error response."""

    payload = {
        "success": False,
        "message": message,
        "code": code,
        "errors": {} if errors is None else errors,
        "meta": meta or {},
    }
    return Response(payload, status=status_code)
