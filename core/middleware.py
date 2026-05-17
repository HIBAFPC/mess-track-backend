"""Middleware for request lifecycle logging and request IDs."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from django.http import HttpRequest, HttpResponse
from rest_framework import status

from core.constants import REQUEST_ID_HEADER

logger = logging.getLogger("mess_track.request")


class RequestLoggingMiddleware:
    """Attach a request id and log the lifecycle of each request."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started_at = time.perf_counter()
        request_id = self._get_request_id(request)
        request.request_id = request_id

        response: HttpResponse | None = None
        try:
            response = self.get_response(request)
            return response
        except Exception:
            logger.exception(
                "Request failed with unhandled exception",
                extra=self._build_log_extra(
                    request=request,
                    response=None,
                    status_code=500,
                    duration_ms=self._duration_ms(started_at),
                ),
            )
            raise
        finally:
            duration_ms = self._duration_ms(started_at)
            status_code = getattr(response, "status_code", 500)
            if response is not None:
                response[REQUEST_ID_HEADER] = request_id

            log_method = (
                logger.warning
                if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
                else logger.info
            )
            log_method(
                "Request completed",
                extra=self._build_log_extra(
                    request=request,
                    response=response,
                    status_code=status_code,
                    duration_ms=duration_ms,
                ),
            )

    def _get_request_id(self, request: HttpRequest) -> str:
        header_key = f"HTTP_{REQUEST_ID_HEADER.upper().replace('-', '_')}"
        return request.META.get(header_key, str(uuid.uuid4()))

    def _duration_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    def _build_log_extra(
        self,
        *,
        request: HttpRequest,
        response: HttpResponse | None,
        status_code: int,
        duration_ms: int,
    ) -> dict[str, Any]:
        user = getattr(request, "user", None)
        user_id = None
        if user is not None and getattr(user, "is_authenticated", False):
            user_id = str(getattr(user, "pk", None))

        return {
            "request_id": getattr(request, "request_id", None),
            "method": request.method,
            "path": request.get_full_path(),
            "status_code": status_code,
            "duration_ms": duration_ms,
            "ip": self._get_client_ip(request),
            "user_id": user_id,
            "error_code": self._get_error_code(response),
        }

    def _get_client_ip(self, request: HttpRequest) -> str | None:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _get_error_code(self, response: HttpResponse | None) -> str | None:
        if response is None:
            return "SERVER_ERROR"
        payload = getattr(response, "data", None)
        if isinstance(payload, dict):
            code = payload.get("code")
            if isinstance(code, str):
                return code
        return None
