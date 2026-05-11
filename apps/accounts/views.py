from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.accounts.serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegistrationSerializer,
    TokenRefreshResponseSerializer,
    UserProfileSerializer,
)
from apps.accounts.services import login_user, logout_user, register_user


class RegisterView(GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegistrationSerializer

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=RegistrationSerializer,
        responses={
            201: AuthResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_payload = register_user(**serializer.validated_data)
        response_serializer = AuthResponseSerializer(auth_payload)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class LoginView(GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=LoginSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Invalid email or password."),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_payload = login_user(request=request, **serializer.validated_data)
        response_serializer = AuthResponseSerializer(auth_payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class LogoutView(GenericAPIView):
    permission_classes = (IsAuthenticatedAndActive,)
    serializer_class = LogoutSerializer

    @extend_schema(
        tags=["Authentication"],
        request=LogoutSerializer,
        responses={
            205: OpenApiResponse(description="Successfully logged out."),
            400: OpenApiResponse(description="Invalid or expired token."),
            401: OpenApiResponse(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout_user(refresh_token=serializer.validated_data["refresh"])
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(RetrieveAPIView):
    permission_classes = (IsAuthenticatedAndActive,)
    serializer_class = UserProfileSerializer

    @extend_schema(
        tags=["Authentication"],
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def get_object(self):
        return self.request.user


class AuthTokenRefreshView(TokenRefreshView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=TokenRefreshSerializer,
        responses={
            200: TokenRefreshResponseSerializer,
            401: OpenApiResponse(description="Invalid or expired token."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
