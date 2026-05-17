from django.contrib import admin

from apps.messes.models import Mess, MessSettings
from apps.messes.services import create_mess


@admin.register(Mess)
class MessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "owner",
        "contact_email",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at", "owner__role")
    search_fields = (
        "name",
        "slug",
        "description",
        "address",
        "contact_email",
        "contact_phone",
        "owner__email",
    )
    readonly_fields = ("slug", "created_at", "updated_at")
    autocomplete_fields = ("owner",)
    list_select_related = ("owner",)
    fieldsets = (
        (
            "Mess details",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "address",
                    "contact_email",
                    "contact_phone",
                    "owner",
                    "is_active",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        created_mess = create_mess(
            name=obj.name,
            owner=obj.owner,
            description=obj.description,
            address=obj.address,
            contact_email=obj.contact_email,
            contact_phone=obj.contact_phone,
        )
        obj.pk = created_mess.pk
        obj.slug = created_mess.slug
        obj.created_at = created_mess.created_at
        obj.updated_at = created_mess.updated_at


@admin.register(MessSettings)
class MessSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "mess",
        "timezone",
        "currency",
        "attendance_default_behavior",
        "billing_mode",
        "updated_at",
    )
    list_select_related = ("mess",)
    search_fields = ("mess__name", "mess__slug")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("mess",)

    def has_add_permission(self, request):
        return False
