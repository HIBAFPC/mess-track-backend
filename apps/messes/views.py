from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.messes.models import Mess
from apps.messes.permissions import IsMessManager, IsMessOwnerOrSuperAdmin
from apps.messes.serializers import (
    MessCreateSerializer,
    MessDeleteSuccessResponseSerializer,
    MessDetailSerializer,
    MessListSerializer,
    MessListSuccessResponseSerializer,
    MessSettingsSerializer,
    MessSettingsSuccessResponseSerializer,
    MessSuccessResponseSerializer,
    MessUpdateSerializer,
)
from apps.messes.services import (
    create_mess,
    deactivate_mess,
    update_mess,
    update_mess_settings,
)
from core.responses import success_response

logger = logging.getLogger("mess_track.messes")


AUTH_401_RESPONSE = OpenApiResponse(
    description="Authentication credentials were not provided."
)
PERMISSION_403_RESPONSE = OpenApiResponse(
    description="You do not have permission to perform this action."
)
MESS_404_RESPONSE = OpenApiResponse(description="Mess not found.")


class MessListCreateView(GenericAPIView):
    permission_classes = (IsAuthenticatedAndActive, IsMessManager)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MessCreateSerializer
        return MessListSerializer

    def get_queryset(self):
        queryset = Mess.objects.select_related("owner").order_by("name", "id")
        user = self.request.user

        if user.role == User.Role.SUPER_ADMIN:
            include_inactive = (
                self.request.query_params.get("include_inactive", "").lower() == "true"
            )
            if include_inactive:
                return queryset
            return queryset.filter(is_active=True)

        return queryset.filter(owner=user, is_active=True)

    @extend_schema(
        tags=["Messes"],
        parameters=[
            OpenApiParameter(
                name="include_inactive",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Include inactive messes. Supported for super admins only.",
                required=False,
            )
        ],
        responses={
            200: MessListSuccessResponseSerializer,
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
        },
    )
    def get(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return success_response(
            message="Messes fetched successfully",
            data=serializer.data,
        )

    @extend_schema(
        tags=["Messes"],
        request=MessCreateSerializer,
        responses={
            201: MessSuccessResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mess = create_mess(**serializer.validated_data)
        response_serializer = MessDetailSerializer(mess)

        logger.info(
            "Mess created via API",
            extra={
                "mess_id": mess.id,
                "owner_id": mess.owner_id,
                "user_id": request.user.id,
            },
        )
        return success_response(
            message="Mess created successfully",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class MessDetailView(GenericAPIView):
    permission_classes = (
        IsAuthenticatedAndActive,
        IsMessManager,
        IsMessOwnerOrSuperAdmin,
    )

    def get_queryset(self):
        return Mess.objects.select_related("owner", "settings")

    def get_object(self):
        mess = get_object_or_404(self.get_queryset(), pk=self.kwargs["id"])
        self.check_object_permissions(self.request, mess)
        return mess

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return MessUpdateSerializer
        return MessDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self, "_mess"):
            context["mess"] = self._mess
        return context

    @extend_schema(
        tags=["Messes"],
        responses={
            200: MessSuccessResponseSerializer,
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
            404: MESS_404_RESPONSE,
        },
    )
    def get(self, request, id: int):
        self._mess = self.get_object()
        serializer = self.get_serializer(self._mess)
        return success_response(
            message="Mess fetched successfully",
            data=serializer.data,
        )

    @extend_schema(
        tags=["Messes"],
        request=MessUpdateSerializer,
        responses={
            200: MessSuccessResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
            404: MESS_404_RESPONSE,
        },
    )
    def patch(self, request, id: int):
        self._mess = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        mess = update_mess(
            mess=self._mess,
            actor=request.user,
            **serializer.validated_data,
        )
        response_serializer = MessDetailSerializer(mess)

        logger.info(
            "Mess updated via API",
            extra={
                "mess_id": mess.id,
                "user_id": request.user.id,
            },
        )
        return success_response(
            message="Mess updated successfully",
            data=response_serializer.data,
        )

    @extend_schema(
        tags=["Messes"],
        responses={
            200: MessDeleteSuccessResponseSerializer,
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
            404: MESS_404_RESPONSE,
        },
    )
    def delete(self, request, id: int):
        mess = self.get_object()
        deactivate_mess(mess=mess, actor=request.user)

        logger.info(
            "Mess deactivated via API",
            extra={
                "mess_id": mess.id,
                "user_id": request.user.id,
            },
        )
        return success_response(
            message="Mess deactivated successfully",
            data=None,
            allow_null_data=True,
            status_code=status.HTTP_200_OK,
        )


class MessSettingsDetailView(GenericAPIView):
    permission_classes = (
        IsAuthenticatedAndActive,
        IsMessManager,
        IsMessOwnerOrSuperAdmin,
    )
    serializer_class = MessSettingsSerializer

    def get_queryset(self):
        return Mess.objects.select_related("owner", "settings")

    def get_object(self):
        mess = get_object_or_404(self.get_queryset(), pk=self.kwargs["id"])
        self.check_object_permissions(self.request, mess)
        return mess

    @extend_schema(
        tags=["Mess Settings"],
        responses={
            200: MessSettingsSuccessResponseSerializer,
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
            404: MESS_404_RESPONSE,
        },
    )
    def get(self, request, id: int):
        mess = self.get_object()
        serializer = self.get_serializer(mess.settings)
        return success_response(
            message="Mess settings fetched successfully",
            data=serializer.data,
        )

    @extend_schema(
        tags=["Mess Settings"],
        request=MessSettingsSerializer,
        responses={
            200: MessSettingsSuccessResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: AUTH_401_RESPONSE,
            403: PERMISSION_403_RESPONSE,
            404: MESS_404_RESPONSE,
        },
    )
    def patch(self, request, id: int):
        mess = self.get_object()
        serializer = self.get_serializer(mess.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        settings_obj = update_mess_settings(
            mess=mess,
            actor=request.user,
            **serializer.validated_data,
        )

        logger.info(
            "Mess settings updated via API",
            extra={
                "mess_id": mess.id,
                "mess_settings_id": settings_obj.id,
                "user_id": request.user.id,
            },
        )
        return success_response(
            message="Mess settings updated successfully",
            data=self.get_serializer(settings_obj).data,
        )
