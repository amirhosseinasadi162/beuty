from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("-created_at",)
    list_display = (
        "phone",
        "phone_verified",
        "is_active",
        "is_staff",
        "created_at",
    )
    search_fields = ("phone",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (
            "Status",
            {
                "fields": (
                    "phone_verified",
                    "is_active",
                    "is_staff",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
    )