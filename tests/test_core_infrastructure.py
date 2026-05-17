from __future__ import annotations

import pytest
from rest_framework import status

from core.constants import REQUEST_ID_HEADER

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.test_urls")]


@pytest.fixture(autouse=True)
def disable_ssl_redirect(settings):
    settings.SECURE_SSL_REDIRECT = False


def test_success_response_helper_returns_standard_shape(api_client):
    response = api_client.get("/success/", HTTP_X_REQUEST_ID="req-success-123")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers[REQUEST_ID_HEADER] == "req-success-123"
    assert response.json() == {
        "success": True,
        "message": "Fetched successfully",
        "data": {"value": 42},
        "meta": {"source": "test-view"},
    }


def test_validation_errors_follow_unified_error_shape(api_client):
    response = api_client.post("/validation-error/", data={}, format="json")

    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"] == {"name": ["This field is required."]}
    assert "request_id" in body["meta"]


def test_application_errors_preserve_structured_code_errors_and_meta(api_client):
    response = api_client.get("/application-error/", HTTP_X_REQUEST_ID="req-app-456")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "success": False,
        "message": "Domain rule failed",
        "code": "DOMAIN_RULE_FAILED",
        "errors": {"field": ["rule violation"]},
        "meta": {"request_id": "req-app-456", "origin": "application"},
    }


def test_unhandled_exceptions_return_safe_500_payload(api_client):
    api_client.raise_request_exception = False
    response = api_client.get("/server-error/", HTTP_X_REQUEST_ID="req-500-789")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "success": False,
        "message": "An unexpected error occurred",
        "code": "SERVER_ERROR",
        "errors": {},
        "meta": {"request_id": "req-500-789"},
    }


def test_method_not_allowed_uses_unified_error_shape(api_client):
    response = api_client.post("/success/", data={}, format="json")

    body = response.json()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert body["success"] is False
    assert body["code"] == "METHOD_NOT_ALLOWED"
    assert body["message"] == 'Method "POST" not allowed.'
    assert body["errors"] == {}
    assert "request_id" in body["meta"]
