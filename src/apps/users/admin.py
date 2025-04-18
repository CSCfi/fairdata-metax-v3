from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext as _

from apps.users.forms import OptionalPasswordUserCreationForm
from apps.users.models import MetaxUser


class MetaxUserAdmin(BaseUserAdmin):
    add_form = OptionalPasswordUserCreationForm

    def get_fieldsets(self, request, obj=None):
        # Superuser can overwrite password and see personal data
        is_superuser = request.user.is_superuser

        basic_fields = ("username",)
        if is_superuser:
            if obj is None:
                basic_fields = ("username", "password1", "password2")
            else:
                basic_fields = ("username", "password")

        fieldsets = [
            (None, {"fields": basic_fields}),
            (
                "Fairdata",
                {
                    "fields": (
                        "fairdata_username",
                        "csc_projects",
                        "synced",
                        "organization",
                    )
                },
            ),
        ]

        if is_superuser:
            # Personal fields from BaseUserAdmin
            fieldsets.append(
                (_("Personal info"), {"fields": ("first_name", "last_name", "email")})
            )

        # Remaining fields from BaseUserAdmin
        fieldsets.extend(
            [
                (
                    _("Permissions"),
                    {
                        "fields": (
                            "is_active",
                            "is_staff",
                            "is_superuser",
                            "groups",
                            "user_permissions",
                        ),
                    },
                ),
                (_("Important dates"), {"fields": ("last_login", "date_joined")}),
            ]
        )
        return fieldsets


admin.site.register(MetaxUser, MetaxUserAdmin)
