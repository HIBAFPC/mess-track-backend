from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.accounts.serializers import (
    AuthResponseSerializer,
    AuthSuccessResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    LogoutSuccessResponseSerializer,
    RegistrationSerializer,
    TokenRefreshResponseSerializer,
    TokenRefreshSuccessResponseSerializer,
    UserProfileSerializer,
    UserProfileSuccessResponseSerializer,
)
from apps.accounts.services import login_user, logout_user, register_user
from core.responses import success_response


class RegisterView(GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegistrationSerializer

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=RegistrationSerializer,
        responses={
            201: AuthSuccessResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_payload = register_user(**serializer.validated_data)
        response_serializer = AuthResponseSerializer(auth_payload)
        return success_response(
            message="User registered successfully",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["Authentication"],
        auth=[],
        request=LoginSerializer,
        responses={
            200: AuthSuccessResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Invalid email or password."),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_payload = login_user(request=request, **serializer.validated_data)
        response_serializer = AuthResponseSerializer(auth_payload)
        return success_response(
            message="Login successful",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )


class LogoutView(GenericAPIView):
    permission_classes = (IsAuthenticatedAndActive,)
    serializer_class = LogoutSerializer

    @extend_schema(
        tags=["Authentication"],
        request=LogoutSerializer,
        responses={
            200: LogoutSuccessResponseSerializer,
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
        return success_response(
            message="Logout successful",
            data={},
            status_code=status.HTTP_200_OK,
        )


class MeView(RetrieveAPIView):
    permission_classes = (IsAuthenticatedAndActive,)
    serializer_class = UserProfileSerializer

    @extend_schema(
        tags=["Authentication"],
        responses={
            200: UserProfileSuccessResponseSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return success_response(
            message="User profile fetched successfully",
            data=serializer.data,
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
            200: TokenRefreshSuccessResponseSerializer,
            401: OpenApiResponse(description="Invalid or expired token."),
        },
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response_serializer = TokenRefreshResponseSerializer(response.data)
        return success_response(
            message="Token refreshed successfully",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )
