from django import forms
from django.contrib import admin
from django.db.models import Case, When

from apps.actors.models import Actor, Organization, Person


class OrganizationAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(
            id=self.instance.id
        )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    form = OrganizationAdminForm
    search_fields = ("url", "pref_label")
    list_display = ("id", "url", "label_en", "parent_label")
    ordering = ["url"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("parent", "children")

    @admin.display(description="parent")
    def parent_label(self, obj):
        if obj.parent:
            return obj.parent.get_label()
        return None

    @admin.display(
        description="pref_label",
        ordering=Case(  # allow sorting by label, prioritize English if available
            When(pref_label__en__isnull=False, then="pref_label__en"),
            default="pref_label__fi",
        ),
    )
    def label_en(self, obj):
        return obj.get_label()


@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = (
        "person",
        "organization",
    )

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
