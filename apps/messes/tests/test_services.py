from __future__ import annotations

from datetime import time

import pytest
from rest_framework import status

from apps.accounts.models import User
from apps.messes.models import MessSettings
from apps.messes.services import (
    MessDomainError,
    create_mess,
    deactivate_mess,
    generate_unique_mess_slug,
    initialize_mess_settings,
    validate_mess_ownership,
)

pytestmark = pytest.mark.django_db

CUSTOM_GRACE_PERIOD_MINUTES = 20


def test_create_mess_initializes_default_settings():
    owner = User.objects.create_user(
        email="admin@example.com",
        password="testpass123",
        role=User.Role.MESS_ADMIN,
    )

    mess = create_mess(name="Sunrise Mess", owner=owner)

    mess.refresh_from_db()
    settings = mess.settings

    assert mess.slug == "sunrise-mess"
    assert mess.owner == owner
    assert mess.is_active is True
    assert settings.timezone == "UTC"
    assert settings.currency == "INR"
    assert settings.default_cutoff_time == time(hour=9, minute=0)
    assert settings.allow_late_changes is False
    assert settings.grace_period_minutes == 0
    assert (
        settings.attendance_default_behavior
        == MessSettings.AttendanceDefaultBehavior.COUNT_ABSENT_IF_NO_ACTION
    )
    assert settings.billing_mode == MessSettings.BillingMode.FIXED_MONTHLY


def test_create_mess_allows_settings_overrides():
    owner = User.objects.create_user(
        email="super@example.com",
        password="testpass123",
        role=User.Role.SUPER_ADMIN,
    )

    mess = create_mess(
        name="Blue Bird",
        owner=owner,
        settings_overrides={
            "timezone": "Asia/Kolkata",
            "currency": "USD",
            "allow_late_changes": True,
            "grace_period_minutes": CUSTOM_GRACE_PERIOD_MINUTES,
            "attendance_default_behavior": (
                MessSettings.AttendanceDefaultBehavior.COUNT_PRESENT_IF_NO_ACTION
            ),
            "billing_mode": MessSettings.BillingMode.PER_MEAL,
        },
    )

    settings = mess.settings

    assert settings.timezone == "Asia/Kolkata"
    assert settings.currency == "USD"
    assert settings.allow_late_changes is True
    assert settings.grace_period_minutes == CUSTOM_GRACE_PERIOD_MINUTES
    assert (
        settings.attendance_default_behavior
        == MessSettings.AttendanceDefaultBehavior.COUNT_PRESENT_IF_NO_ACTION
    )
    assert settings.billing_mode == MessSettings.BillingMode.PER_MEAL


def test_slug_generation_adds_numeric_suffix_for_duplicates():
    owner = User.objects.create_user(
        email="owner@example.com",
        password="testpass123",
        role=User.Role.MESS_ADMIN,
    )
    create_mess(name="Green Leaf", owner=owner)

    slug = generate_unique_mess_slug("Green Leaf")

    assert slug == "green-leaf-2"


def test_initialize_mess_settings_rejects_duplicate_settings():
    owner = User.objects.create_user(
        email="owner2@example.com",
        password="testpass123",
        role=User.Role.MESS_ADMIN,
    )
    mess = create_mess(name="Oak Mess", owner=owner)

    with pytest.raises(MessDomainError) as exc_info:
        initialize_mess_settings(mess=mess)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


def test_residents_cannot_create_mess():
    resident = User.objects.create_user(
        email="resident@example.com",
        password="testpass123",
        role=User.Role.RESIDENT,
    )

    with pytest.raises(MessDomainError) as exc_info:
        create_mess(name="Blocked Mess", owner=resident)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_only_owner_or_super_admin_can_deactivate_mess():
    owner = User.objects.create_user(
        email="owner3@example.com",
        password="testpass123",
        role=User.Role.MESS_ADMIN,
    )
    another_admin = User.objects.create_user(
        email="another@example.com",
        password="testpass123",
        role=User.Role.MESS_ADMIN,
    )
    super_admin = User.objects.create_user(
        email="boss@example.com",
        password="testpass123",
        role=User.Role.SUPER_ADMIN,
    )
    mess = create_mess(name="Lakeside", owner=owner)

    with pytest.raises(MessDomainError):
        validate_mess_ownership(user=another_admin, mess=mess)

    deactivate_mess(mess=mess, actor=super_admin)
    mess.refresh_from_db()

    assert mess.is_active is False
