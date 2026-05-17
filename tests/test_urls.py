from django.urls import path

from tests.test_views import (
    ApplicationErrorView,
    ServerErrorView,
    SuccessView,
    ValidationErrorView,
)

urlpatterns = [
    path("success/", SuccessView.as_view(), name="success"),
    path("validation-error/", ValidationErrorView.as_view(), name="validation-error"),
    path(
        "application-error/",
        ApplicationErrorView.as_view(),
        name="application-error",
    ),
    path("server-error/", ServerErrorView.as_view(), name="server-error"),
]
