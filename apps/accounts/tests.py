import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.permissions import (
    IsAuthenticatedAndActive,
    IsMessAdmin,
    IsResident,
    IsSuperAdmin,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def disable_ssl_redirect(settings):
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def request_factory():
    return APIRequestFactory()


def _auth_headers(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _register_user(api_client, **overrides):
    payload = {
        "email": "user@example.com",
        "password": "StrongPass123!",
        "first_name": "Test",
        "last_name": "User",
    }
    payload.update(overrides)
    return api_client.post("/api/v1/auth/register/", data=payload, format="json")


def _login_user(api_client, *, email, password):
    return api_client.post(
        "/api/v1/auth/login/",
        data={"email": email, "password": password},
        format="json",
    )


def _permission_request(request_factory, user=None):
    django_request = request_factory.get("/api/v1/auth/me/")
    django_request.user = user
    return django_request


def test_register_returns_unified_success_response(api_client):
    response = _register_user(api_client, email="newuser@example.com")

    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["success"] is True
    assert body["message"] == "User registered successfully"
    assert body["data"]["user"]["email"] == "newuser@example.com"
    assert body["data"]["user"]["role"] == User.Role.RESIDENT
    assert body["data"]["tokens"]["access"]
    assert body["data"]["tokens"]["refresh"]
    assert "password" not in body["data"]["user"]
    assert body["meta"] == {}
    user = User.objects.get(email="newuser@example.com")
    assert user.role == User.Role.RESIDENT
    assert user.check_password("StrongPass123!")
    assert user.password != "StrongPass123!"


def test_register_rejects_duplicate_email(api_client):
    User.objects.create_user(email="duplicate@example.com", password="StrongPass123!")

    response = _register_user(api_client, email="duplicate@example.com")
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"] == {
        "email": ["A user with this email address already exists."]
    }


def test_register_rejects_invalid_payload(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        data={"email": "invalid-email"},
        format="json",
    )
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"
    assert "email" in body["errors"]
    assert "password" in body["errors"]


def test_register_enforces_password_validation(api_client):
    response = _register_user(api_client, email="weak@example.com", password="123")
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"
    assert "non_field_errors" in body["errors"]


def test_public_registration_cannot_assign_privileged_role(api_client):
    response = _register_user(
        api_client,
        email="privileged@example.com",
        role=User.Role.SUPER_ADMIN,
    )
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"] == {"role": ["This field is not allowed."]}
    assert not User.objects.filter(email="privileged@example.com").exists()


def test_login_returns_unified_success_response(api_client):
    User.objects.create_user(email="login@example.com", password="StrongPass123!")

    response = _login_user(
        api_client,
        email="login@example.com",
        password="StrongPass123!",
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["success"] is True
    assert body["message"] == "Login successful"
    assert body["data"]["user"]["email"] == "login@example.com"
    assert body["data"]["tokens"]["access"]
    assert body["data"]["tokens"]["refresh"]
    assert "password" not in body["data"]["user"]
    assert body["meta"] == {}


def test_login_rejects_invalid_credentials(api_client):
    response = _login_user(
        api_client,
        email="missing@example.com",
        password="wrongpass",
    )
    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["success"] is False
    assert body["message"] == "Invalid email or password."
    assert body["code"] == "AUTHENTICATION_FAILED"
    assert body["errors"] == {}
    assert "request_id" in body["meta"]


def test_login_rejects_inactive_user(api_client):
    user = User.objects.create_user(
        email="inactive@example.com",
        password="StrongPass123!",
    )
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = _login_user(
        api_client,
        email="inactive@example.com",
        password="StrongPass123!",
    )
    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["success"] is False
    assert body["code"] == "AUTHENTICATION_FAILED"


def test_refresh_returns_unified_success_response(api_client):
    register_response = _register_user(api_client, email="refresh@example.com")
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


def test_refresh_rejects_invalid_token(api_client):
    response = api_client.post(
        "/api/v1/auth/token/refresh/",
        data={"refresh": "invalid-refresh-token"},
        format="json",
    )
    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["success"] is False
    assert body["message"]
    assert body["code"] == "INVALID_TOKEN"
    assert body["errors"] == {}
    assert "request_id" in body["meta"]


def test_logout_blacklists_refresh_token(api_client):
    register_response = _register_user(api_client, email="logout@example.com")
    tokens = register_response.json()["data"]["tokens"]

    logout_response = api_client.post(
        "/api/v1/auth/logout/",
        data={"refresh": tokens["refresh"]},
        format="json",
        **_auth_headers(tokens["access"]),
    )
    refresh_response = api_client.post(
        "/api/v1/auth/token/refresh/",
        data={"refresh": tokens["refresh"]},
        format="json",
    )

    assert logout_response.status_code == status.HTTP_200_OK
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.json()["code"] == "INVALID_TOKEN"


def test_logout_rejects_invalid_token(api_client):
    register_response = _register_user(api_client, email="logout-invalid@example.com")
    access = register_response.json()["data"]["tokens"]["access"]

    response = api_client.post(
        "/api/v1/auth/logout/",
        data={"refresh": "invalid-refresh-token"},
        format="json",
        **_auth_headers(access),
    )
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"] == {"refresh": ["Invalid or expired token."]}


def test_me_returns_unified_success_response(api_client):
    register_response = _register_user(api_client, email="me@example.com")
    access = register_response.json()["data"]["tokens"]["access"]

    response = api_client.get("/api/v1/auth/me/", **_auth_headers(access))
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["success"] is True
    assert body["message"] == "User profile fetched successfully"
    assert body["data"]["email"] == "me@example.com"
    assert body["meta"] == {}


def test_me_rejects_unauthorized_access(api_client):
    response = api_client.get("/api/v1/auth/me/")
    body = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["success"] is False
    assert body["code"] == "NOT_AUTHENTICATED"


def test_is_super_admin_permission(request_factory):
    super_admin = User.objects.create_user(
        email="super@example.com",
        password="StrongPass123!",
        role=User.Role.SUPER_ADMIN,
    )
    resident = User.objects.create_user(
        email="resident1@example.com",
        password="StrongPass123!",
        role=User.Role.RESIDENT,
    )
    permission = IsSuperAdmin()

    assert permission.has_permission(
        _permission_request(request_factory, super_admin),
        None,
    )
    assert not permission.has_permission(
        _permission_request(request_factory, resident),
        None,
    )
    assert not permission.has_permission(_permission_request(request_factory), None)


def test_is_mess_admin_permission(request_factory):
    mess_admin = User.objects.create_user(
        email="mess@example.com",
        password="StrongPass123!",
        role=User.Role.MESS_ADMIN,
    )
    resident = User.objects.create_user(
        email="resident2@example.com",
        password="StrongPass123!",
        role=User.Role.RESIDENT,
    )
    permission = IsMessAdmin()

    assert permission.has_permission(
        _permission_request(request_factory, mess_admin),
        None,
    )
    assert not permission.has_permission(
        _permission_request(request_factory, resident),
        None,
    )


def test_is_resident_permission(request_factory):
    resident = User.objects.create_user(
        email="resident3@example.com",
        password="StrongPass123!",
        role=User.Role.RESIDENT,
    )
    mess_admin = User.objects.create_user(
        email="mess2@example.com",
        password="StrongPass123!",
        role=User.Role.MESS_ADMIN,
    )
    permission = IsResident()

    assert permission.has_permission(
        _permission_request(request_factory, resident),
        None,
    )
    assert not permission.has_permission(
        _permission_request(request_factory, mess_admin),
        None,
    )


def test_is_authenticated_and_active_permission(request_factory):
    active_user = User.objects.create_user(
        email="active@example.com",
        password="StrongPass123!",
    )
    inactive_user = User.objects.create_user(
        email="inactive2@example.com",
        password="StrongPass123!",
    )
    inactive_user.is_active = False
    inactive_user.save(update_fields=["is_active"])
    permission = IsAuthenticatedAndActive()

    assert permission.has_permission(
        _permission_request(request_factory, active_user),
        None,
    )
    assert not permission.has_permission(
        _permission_request(request_factory, inactive_user),
        None,
    )
    assert not permission.has_permission(_permission_request(request_factory), None)


def test_schema_documents_auth_endpoints_and_bearer_security(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")
    schema = response.json()
    paths = schema["paths"]

    assert response.status_code == status.HTTP_200_OK
    assert "/api/v1/auth/register/" in paths
    assert "/api/v1/auth/login/" in paths
    assert "/api/v1/auth/logout/" in paths
    assert "/api/v1/auth/token/refresh/" in paths
    assert "/api/v1/auth/me/" in paths
    assert schema["components"]["securitySchemes"]["jwtAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert "security" not in paths["/api/v1/auth/register/"]["post"]
    assert "security" not in paths["/api/v1/auth/login/"]["post"]
    assert "security" not in paths["/api/v1/auth/token/refresh/"]["post"]
    assert {"jwtAuth": []} in paths["/api/v1/auth/me/"]["get"]["security"]
    assert {"jwtAuth": []} in paths["/api/v1/auth/logout/"]["post"]["security"]
