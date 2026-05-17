from django.contrib.auth import authenticate, get_user_model
from rest_framework import exceptions
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def _build_auth_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        "user": user,
        "tokens": {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
    }


def register_user(*, email, password, first_name="", last_name="", phone_number=""):
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role=User.Role.RESIDENT,
    )
    return _build_auth_response(user)


def login_user(*, email, password, request=None):
    user = authenticate(request=request, email=email, password=password)
    if user is None or not user.is_active:
        raise exceptions.AuthenticationFailed("Invalid email or password.")
    return _build_auth_response(user)


def logout_user(*, refresh_token):
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError as exc:
        raise exceptions.ValidationError(
            {"refresh": ["Invalid or expired token."]}
        ) from exc
