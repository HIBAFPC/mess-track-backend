from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.messes.models import Mess
from apps.messes.services import initialize_mess_settings

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def disable_ssl_redirect(settings):
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def super_admin():
    return User.objects.create_user(
        email="super-admin@example.com",
        password="StrongPass123!",
        role=User.Role.SUPER_ADMIN,
    )


@pytest.fixture
def mess_admin():
    return User.objects.create_user(
        email="mess-admin@example.com",
        password="StrongPass123!",
        role=User.Role.MESS_ADMIN,
    )


@pytest.fixture
def another_mess_admin():
    return User.objects.create_user(
        email="other-admin@example.com",
        password="StrongPass123!",
        role=User.Role.MESS_ADMIN,
    )


@pytest.fixture
def resident():
    return User.objects.create_user(
        email="resident@example.com",
        password="StrongPass123!",
        role=User.Role.RESIDENT,
    )


def _auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_mess_admin_can_create_mess_and_is_forced_as_owner(
    api_client,
    mess_admin,
    super_admin,
):
    client = _auth_client(mess_admin)

    response = client.post(
        "/api/v1/messes/",
        data={
            "name": "Sunrise Mess",
            "owner": super_admin.id,
            "contact_email": "sunrise@example.com",
            "contact_phone": "+91 98765 43210",
        },
        format="json",
    )
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"] == {"owner": ["This field is not allowed."]}


def test_super_admin_can_create_mess_with_explicit_owner(super_admin, mess_admin):
    client = _auth_client(super_admin)

    response = client.post(
        "/api/v1/messes/",
        data={
            "name": "Blue Plate",
            "slug": "blue-plate",
            "owner": mess_admin.id,
            "description": "Main campus mess",
        },
        format="json",
    )
    body = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert body["success"] is True
    assert body["message"] == "Mess created successfully"
    assert body["data"]["slug"] == "blue-plate"
    assert body["data"]["owner"]["id"] == mess_admin.id
    mess = Mess.objects.get(slug="blue-plate")
    assert mess.owner_id == mess_admin.id
    assert hasattr(mess, "settings")


def test_super_admin_create_falls_back_to_self_as_owner(super_admin):
    client = _auth_client(super_admin)

    response = client.post(
        "/api/v1/messes/",
        data={"name": "North Mess"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    mess = Mess.objects.get(name="North Mess")
    assert mess.owner_id == super_admin.id
    assert mess.slug == "north-mess"


def test_resident_cannot_access_mess_management_endpoints(resident):
    client = _auth_client(resident)

    response = client.get("/api/v1/messes/")
    body = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert body["success"] is False
    assert body["code"] == "PERMISSION_DENIED"


def test_super_admin_list_excludes_inactive_by_default(super_admin, mess_admin):
    active_mess = Mess.objects.create(name="Active", slug="active", owner=mess_admin)
    inactive_mess = Mess.objects.create(
        name="Inactive",
        slug="inactive",
        owner=mess_admin,
        is_active=False,
    )

    client = _auth_client(super_admin)
    response = client.get("/api/v1/messes/")

    assert response.status_code == status.HTTP_200_OK
    mess_ids = [item["id"] for item in response.json()["data"]]
    assert active_mess.id in mess_ids
    assert inactive_mess.id not in mess_ids


def test_super_admin_can_include_inactive_messes(super_admin, mess_admin):
    inactive_mess = Mess.objects.create(
        name="Dormant",
        slug="dormant",
        owner=mess_admin,
        is_active=False,
    )

    client = _auth_client(super_admin)
    response = client.get("/api/v1/messes/?include_inactive=true")

    assert response.status_code == status.HTTP_200_OK
    mess_ids = [item["id"] for item in response.json()["data"]]
    assert inactive_mess.id in mess_ids


def test_mess_admin_list_returns_only_owned_active_messes(
    mess_admin,
    another_mess_admin,
):
    owned_mess = Mess.objects.create(
        name="Owned",
        slug="owned",
        owner=mess_admin,
    )
    Mess.objects.create(
        name="Owned Inactive",
        slug="owned-inactive",
        owner=mess_admin,
        is_active=False,
    )
    Mess.objects.create(
        name="Foreign",
        slug="foreign",
        owner=another_mess_admin,
    )

    client = _auth_client(mess_admin)
    response = client.get("/api/v1/messes/?include_inactive=true")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert [item["id"] for item in body["data"]] == [owned_mess.id]


def test_mess_detail_is_owner_restricted(mess_admin, another_mess_admin):
    mess = Mess.objects.create(
        name="Restricted",
        slug="restricted",
        owner=another_mess_admin,
    )

    client = _auth_client(mess_admin)
    response = client.get(f"/api/v1/messes/{mess.id}/")
    body = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert body["success"] is False
    assert body["code"] == "PERMISSION_DENIED"


def test_owner_can_retrieve_inactive_mess(mess_admin):
    mess = Mess.objects.create(
        name="Inactive Owned",
        slug="inactive-owned",
        owner=mess_admin,
        is_active=False,
    )

    client = _auth_client(mess_admin)
    response = client.get(f"/api/v1/messes/{mess.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["id"] == mess.id


def test_owner_can_patch_mess_metadata_and_activation(mess_admin):
    mess = Mess.objects.create(
        name="Old Name",
        slug="old-name",
        owner=mess_admin,
        is_active=False,
    )

    client = _auth_client(mess_admin)
    response = client.patch(
        f"/api/v1/messes/{mess.id}/",
        data={
            "name": "New Name",
            "slug": "new-name",
            "contact_phone": "+1 555 010 1000",
            "is_active": True,
        },
        format="json",
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["data"]["name"] == "New Name"
    assert body["data"]["slug"] == "new-name"
    assert body["data"]["is_active"] is True
    mess.refresh_from_db()
    assert mess.is_active is True


def test_delete_soft_deactivates_mess_and_returns_null_data(mess_admin):
    mess = Mess.objects.create(
        name="To Delete",
        slug="to-delete",
        owner=mess_admin,
    )

    client = _auth_client(mess_admin)
    response = client.delete(f"/api/v1/messes/{mess.id}/")
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body == {
        "success": True,
        "message": "Mess deactivated successfully",
        "data": None,
        "meta": {},
    }
    mess.refresh_from_db()
    assert mess.is_active is False


def test_slug_must_be_unique_on_create(super_admin):
    Mess.objects.create(name="Existing", slug="existing", owner=super_admin)
    client = _auth_client(super_admin)

    response = client.post(
        "/api/v1/messes/",
        data={"name": "Another", "slug": "existing"},
        format="json",
    )
    body = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"] == {"slug": ["A mess with this slug already exists."]}


def test_settings_endpoint_allows_owner_to_retrieve_and_update(mess_admin):
    mess = Mess.objects.create(
        name="Settings Mess",
        slug="settings-mess",
        owner=mess_admin,
    )
    initialize_mess_settings(mess=mess)

    client = _auth_client(mess_admin)
    retrieve_response = client.get(f"/api/v1/messes/{mess.id}/settings/")
    update_response = client.patch(
        f"/api/v1/messes/{mess.id}/settings/",
        data={
            "timezone": "Asia/Kolkata",
            "currency": "USD",
            "allow_late_changes": True,
            "grace_period_minutes": 15,
            "billing_mode": "PER_MEAL",
        },
        format="json",
    )

    assert retrieve_response.status_code == status.HTTP_200_OK
    assert update_response.status_code == status.HTTP_200_OK
    updated_body = update_response.json()
    assert updated_body["data"]["timezone"] == "Asia/Kolkata"
    assert updated_body["data"]["billing_mode"] == "PER_MEAL"
    mess.settings.refresh_from_db()
    assert mess.settings.currency == "USD"


def test_settings_endpoint_is_owner_restricted(mess_admin, another_mess_admin):
    mess = Mess.objects.create(
        name="Private Settings",
        slug="private-settings",
        owner=another_mess_admin,
    )
    initialize_mess_settings(mess=mess)

    client = _auth_client(mess_admin)
    response = client.get(f"/api/v1/messes/{mess.id}/settings/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_schema_documents_mess_endpoints(super_admin):
    client = _auth_client(super_admin)
    response = client.get("/api/schema/", HTTP_ACCEPT="application/json")
    schema = response.json()
    paths = schema["paths"]

    assert response.status_code == status.HTTP_200_OK
    assert "/api/v1/messes/" in paths
    assert "/api/v1/messes/{id}/" in paths
    assert "/api/v1/messes/{id}/settings/" in paths
    assert {"jwtAuth": []} in paths["/api/v1/messes/"]["get"]["security"]
    assert {"jwtAuth": []} in paths["/api/v1/messes/"]["post"]["security"]
