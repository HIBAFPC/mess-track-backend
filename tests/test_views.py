from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.exceptions import ApplicationError
from core.responses import success_response


class SuccessView(APIView):
    permission_classes: ClassVar = (AllowAny,)

    def get(self, request):
        return success_response(
            message="Fetched successfully",
            data={"value": 42},
            meta={"source": "test-view"},
        )


class ValidationErrorSerializer(serializers.Serializer):
    name = serializers.CharField()


class ValidationErrorView(APIView):
    permission_classes: ClassVar = (AllowAny,)

    def post(self, request):
        serializer = ValidationErrorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(data=serializer.validated_data)


class ApplicationErrorView(APIView):
    permission_classes: ClassVar = (AllowAny,)

    def get(self, request):
        raise ApplicationError(
            detail="Domain rule failed",
            code="DOMAIN_RULE_FAILED",
            errors={"field": ["rule violation"]},
            meta={"origin": "application"},
            status_code=status.HTTP_409_CONFLICT,
        )


class ServerErrorView(APIView):
    permission_classes: ClassVar = (AllowAny,)

    def get(self, request):
        raise RuntimeError("unexpected boom")
