from __future__ import annotations

import re

from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.serializers import (
    BaseSuccessResponseSerializer,
    EmptyResponseDataSerializer,
)
from apps.messes.models import Mess, MessSettings
from apps.messes.services import generate_unique_mess_slug

User = get_user_model()

PHONE_REGEX = re.compile(r"^[0-9+() -]{7,20}$")


class MessOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")
        read_only_fields = fields


class MessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessSettings
        exclude = ("id", "mess", "created_at", "updated_at")


class MessListSerializer(serializers.ModelSerializer):
    owner = MessOwnerSerializer(read_only=True)

    class Meta:
        model = Mess
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "address",
            "contact_email",
            "contact_phone",
            "owner",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MessDetailSerializer(MessListSerializer):
    settings = MessSettingsSerializer(read_only=True)

    class Meta(MessListSerializer.Meta):
        fields = (*MessListSerializer.Meta.fields, "settings")


class MessCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
    )

    def validate_contact_phone(self, value: str) -> str:
        if value and not PHONE_REGEX.fullmatch(value):
            raise serializers.ValidationError("Enter a valid contact phone number.")
        return value

    def validate_slug(self, value: str) -> str:
        if not value:
            return value
        normalized = slugify(value).strip("-")
        if not normalized:
            raise serializers.ValidationError("Enter a valid slug.")
        if Mess.objects.filter(slug=normalized).exists():
            raise serializers.ValidationError("A mess with this slug already exists.")
        return normalized

    def validate_owner(self, value: User) -> User:
        if value.role not in {User.Role.SUPER_ADMIN, User.Role.MESS_ADMIN}:
            raise serializers.ValidationError(
                "Owner must be a super admin or mess admin."
            )
        return value

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        if user.role != User.Role.SUPER_ADMIN and "owner" in self.initial_data:
            raise serializers.ValidationError({"owner": ["This field is not allowed."]})

        if not attrs.get("slug"):
            generated_slug = generate_unique_mess_slug(attrs["name"])
            attrs["slug"] = generated_slug

        attrs["owner"] = attrs.get("owner", user)
        return attrs


class MessUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    slug = serializers.SlugField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )
    is_active = serializers.BooleanField(required=False)

    def validate_contact_phone(self, value: str) -> str:
        if value and not PHONE_REGEX.fullmatch(value):
            raise serializers.ValidationError("Enter a valid contact phone number.")
        return value

    def validate_slug(self, value: str) -> str:
        normalized = slugify(value).strip("-")
        if not normalized:
            raise serializers.ValidationError("Enter a valid slug.")

        mess: Mess = self.context["mess"]
        if Mess.objects.exclude(pk=mess.pk).filter(slug=normalized).exists():
            raise serializers.ValidationError("A mess with this slug already exists.")
        return normalized


class MessSuccessResponseSerializer(BaseSuccessResponseSerializer):
    data = MessDetailSerializer(read_only=True)


class MessListSuccessResponseSerializer(BaseSuccessResponseSerializer):
    data = MessListSerializer(many=True, read_only=True)


class MessSettingsSuccessResponseSerializer(BaseSuccessResponseSerializer):
    data = MessSettingsSerializer(read_only=True)


class MessDeleteSuccessResponseSerializer(BaseSuccessResponseSerializer):
    data = EmptyResponseDataSerializer(read_only=True, allow_null=True)
