from django import forms
from django.contrib import admin
from pkg_resources import require

from apps.refdata.models import FieldOfScience


class ReferenceDataAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["broader"].queryset = self.fields["broader"].queryset.exclude(
            id=self.instance.id
        )


class AbstractConceptAdmin(admin.ModelAdmin):
    form = ReferenceDataAdminForm
    list_display = ("id", "url", "label_en", "broader_concept")

    @admin.display(description="broader")
    def broader_concept(self, obj):
        return [parent.pref_label.get("en") for parent in obj.broader.all()]

    @admin.display(description="pref_label")
    def label_en(self, obj):
        return obj.pref_label.get("en") or next(iter(obj.pref_label.values()), "")


@admin.register(FieldOfScience)
class FieldOfScienceReferenceDataAdmin(AbstractConceptAdmin):
    ordering = ["url"]
