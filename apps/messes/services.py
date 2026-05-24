from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import User
from apps.messes.models import Mess, MessSettings
from apps.messes.permissions import ALLOWED_MESS_MANAGEMENT_ROLES
from core.constants import ERROR_CODE_PERMISSION_DENIED, ERROR_CODE_VALIDATION
from core.exceptions import ApplicationError

logger = logging.getLogger("mess_track.messes")


class MessDomainError(ApplicationError):
    default_detail = "Mess operation could not be completed"
    default_code = ERROR_CODE_VALIDATION


def create_mess(  # noqa: PLR0913
    *,
    name: str,
    owner: User,
    slug: str | None = None,
    description: str = "",
    address: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    settings_overrides: Mapping[str, Any] | None = None,
) -> Mess:
    validate_mess_management_access(user=owner)

    slug = slug or generate_unique_mess_slug(name)
    settings_payload = dict(settings_overrides or {})

    with transaction.atomic():
        mess = Mess.objects.create(
            name=name,
            slug=slug,
            description=description,
            address=address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            owner=owner,
        )
        initialize_mess_settings(mess=mess, overrides=settings_payload)

    logger.info(
        "Created mess",
        extra={
            "mess_id": mess.id,
            "owner_id": owner.id,
        },
    )
    return mess


def initialize_mess_settings(
    *, mess: Mess, overrides: Mapping[str, Any] | None = None
) -> MessSettings:
    settings_defaults = {
        "timezone": "UTC",
        "currency": "INR",
        "default_cutoff_time": MessSettings._meta.get_field(
            "default_cutoff_time"
        ).get_default(),
        "allow_late_changes": False,
        "grace_period_minutes": 0,
        "attendance_default_behavior": (
            MessSettings.AttendanceDefaultBehavior.COUNT_ABSENT_IF_NO_ACTION
        ),
        "billing_mode": MessSettings.BillingMode.FIXED_MONTHLY,
    }
    if overrides:
        settings_defaults.update(overrides)

    settings_obj, created = MessSettings.objects.get_or_create(
        mess=mess,
        defaults=settings_defaults,
    )
    if not created:
        raise MessDomainError(
            "Settings have already been initialized for this mess",
            code=ERROR_CODE_VALIDATION,
            errors={"mess": ["Settings already exist for this mess."]},
        )

    logger.info(
        "Initialized mess settings",
        extra={
            "mess_id": mess.id,
            "mess_settings_id": settings_obj.id,
        },
    )
    return settings_obj


def deactivate_mess(*, mess: Mess, actor: User) -> Mess:
    validate_mess_ownership(user=actor, mess=mess)
    if not mess.is_active:
        return mess

    mess.is_active = False
    mess.save(update_fields=["is_active", "updated_at"])

    logger.info(
        "Deactivated mess",
        extra={
            "mess_id": mess.id,
            "actor_id": actor.id,
        },
    )
    return mess


def update_mess(*, mess: Mess, actor: User, **updates: Any) -> Mess:
    validate_mess_ownership(user=actor, mess=mess)
    if not updates:
        return mess

    for field, value in updates.items():
        setattr(mess, field, value)

    updated_fields = list(updates.keys())
    if "updated_at" not in updated_fields:
        updated_fields.append("updated_at")
    mess.save(update_fields=updated_fields)

    logger.info(
        "Updated mess",
        extra={
            "mess_id": mess.id,
            "actor_id": actor.id,
        },
    )
    return mess


def update_mess_settings(
    *, mess: Mess, actor: User, **updates: Any
) -> MessSettings:
    validate_mess_ownership(user=actor, mess=mess)
    settings_obj = mess.settings
    if not updates:
        return settings_obj

    for field, value in updates.items():
        setattr(settings_obj, field, value)

    updated_fields = list(updates.keys())
    if "updated_at" not in updated_fields:
        updated_fields.append("updated_at")
    settings_obj.save(update_fields=updated_fields)

    logger.info(
        "Updated mess settings",
        extra={
            "mess_id": mess.id,
            "mess_settings_id": settings_obj.id,
            "actor_id": actor.id,
        },
    )
    return settings_obj


def validate_mess_management_access(*, user: User) -> None:
    if not user.is_active or user.role not in ALLOWED_MESS_MANAGEMENT_ROLES:
        raise MessDomainError(
            "You do not have permission to manage messes",
            code=ERROR_CODE_PERMISSION_DENIED,
            errors={"user": ["Only super admins and mess admins can manage messes."]},
            status_code=403,
        )


def validate_mess_ownership(*, user: User, mess: Mess) -> None:
    validate_mess_management_access(user=user)
    if user.role == User.Role.SUPER_ADMIN:
        return
    if mess.owner_id != user.id:
        raise MessDomainError(
            "You do not have access to this mess",
            code=ERROR_CODE_PERMISSION_DENIED,
            errors={"mess": ["You are not the owner of this mess."]},
            status_code=403,
        )


def generate_unique_mess_slug(name: str) -> str:
    base_slug = slugify(name).strip("-") or "mess"
    slug = base_slug
    suffix = 2

    while Mess.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    return slug
