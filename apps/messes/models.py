from __future__ import annotations

from datetime import time

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Mess(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_messes",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        indexes = (
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["owner", "is_active"]),
        )

    def __str__(self) -> str:
        return self.name


class MessSettings(models.Model):
    class AttendanceDefaultBehavior(models.TextChoices):
        COUNT_PRESENT_IF_NO_ACTION = (
            "COUNT_PRESENT_IF_NO_ACTION",
            _("Count present if no action"),
        )
        COUNT_ABSENT_IF_NO_ACTION = (
            "COUNT_ABSENT_IF_NO_ACTION",
            _("Count absent if no action"),
        )

    class BillingMode(models.TextChoices):
        FIXED_MONTHLY = "FIXED_MONTHLY", _("Fixed monthly")
        PER_MEAL = "PER_MEAL", _("Per meal")

    mess = models.OneToOneField(
        Mess,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=3, default="INR")
    default_cutoff_time = models.TimeField(default=time(hour=9, minute=0))
    allow_late_changes = models.BooleanField(default=False)
    grace_period_minutes = models.PositiveIntegerField(default=0)
    attendance_default_behavior = models.CharField(
        max_length=32,
        choices=AttendanceDefaultBehavior.choices,
        default=AttendanceDefaultBehavior.COUNT_ABSENT_IF_NO_ACTION,
    )
    billing_mode = models.CharField(
        max_length=32,
        choices=BillingMode.choices,
        default=BillingMode.FIXED_MONTHLY,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Mess settings"

    def __str__(self) -> str:
        return f"Settings for {self.mess.name}"
