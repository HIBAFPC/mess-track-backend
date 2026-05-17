import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def _auth_headers(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def test_register_returns_unified_success_response(api_client, settings):
    settings.SECURE_SSL_REDIRECT = False

    response = api_client.post(
        "/api/v1/auth/register/",
        data={
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "first_name": "New",
            "last_name": "User",
        },
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["success"] is True
    assert body["message"] == "User registered successfully"
    assert body["data"]["user"]["email"] == "newuser@example.com"
    assert body["data"]["tokens"]["access"]
    assert body["data"]["tokens"]["refresh"]
    assert body["meta"] == {}


def test_login_returns_unified_success_response(api_client, settings):
    settings.SECURE_SSL_REDIRECT = False
    User.objects.create_user(email="login@example.com", password="StrongPass123!")

    response = api_client.post(
        "/api/v1/auth/login/",
        data={"email": "login@example.com", "password": "StrongPass123!"},
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["success"] is True
    assert body["message"] == "Login successful"
    assert body["data"]["user"]["email"] == "login@example.com"
    assert body["data"]["tokens"]["access"]
    assert body["data"]["tokens"]["refresh"]
    assert body["meta"] == {}


def test_login_failure_uses_unified_error_response(api_client, settings):
    settings.SECURE_SSL_REDIRECT = False

    response = api_client.post(
        "/api/v1/auth/login/",
        data={"email": "missing@example.com", "password": "wrongpass"},
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["success"] is False
    assert body["message"] == "Invalid email or password."
    assert body["code"] == "AUTHENTICATION_FAILED"
    assert body["errors"] == {}
    assert "request_id" in body["meta"]


def test_me_returns_unified_success_response(api_client, settings):
    settings.SECURE_SSL_REDIRECT = False
    register_response = api_client.post(
        "/api/v1/auth/register/",
        data={
            "email": "me@example.com",
            "password": "StrongPass123!",
            "first_name": "Me",
        },
        format="json",
    )
    access = register_response.json()["data"]["tokens"]["access"]

    response = api_client.get("/api/v1/auth/me/", **_auth_headers(access))

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["success"] is True
    assert body["message"] == "User profile fetched successfully"
    assert body["data"]["email"] == "me@example.com"
    assert body["meta"] == {}


def test_refresh_returns_unified_success_response(api_client, settings):
    settings.SECURE_SSL_REDIRECT = False
    register_response = api_client.post(
        "/api/v1/auth/register/",
        data={
            "email": "refresh@example.com",
            "password": "StrongPass123!",
        },
        format="json",
    )
    refresh = register_response.json()["data"]["tokens"]["refresh"]

    response = api_client.post(
        "/api/v1/auth/token/refresh/",
        data={"refresh": refresh},
        format="json",
    )

    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["success"] is True
    assert body["message"] == "Token refreshed successfully"
    assert body["data"]["access"]
    assert body["meta"] == {}


def test_logout_returns_unified_success_response(api_client, settings):
    settings.SECURE_SSL_REDIRECT = False
    register_response = api_client.post(
        "/api/v1/auth/register/",
        data={
            "email": "logout@example.com",
            "password": "StrongPass123!",
        },
        format="json",
    )
    auth_data = register_response.json()["data"]["tokens"]

    response = api_client.post(
        "/api/v1/auth/logout/",
        data={"refresh": auth_data["refresh"]},
        format="json",
        **_auth_headers(auth_data["access"]),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "success": True,
        "message": "Logout successful",
        "data": {},
        "meta": {},
    }
