from django.urls import path

from apps.messes.views import (
    MessDetailView,
    MessListCreateView,
    MessSettingsDetailView,
)

urlpatterns = [
    path("", MessListCreateView.as_view(), name="mess-list-create"),
    path("<int:id>/", MessDetailView.as_view(), name="mess-detail"),
    path(
        "<int:id>/settings/",
        MessSettingsDetailView.as_view(),
        name="mess-settings-detail",
    ),
]
