from django import forms
from django.contrib import admin
from django.db.models import Case, F, When

from apps.refdata.models import reference_data_models


class ReferenceDataAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["broader"].queryset = self.fields["broader"].queryset.exclude(
            id=self.instance.id
        )


class AbstractConceptAdmin(admin.ModelAdmin):
    form = ReferenceDataAdminForm
    search_fields = ("url", "pref_label")
    list_display = ("id", "url", "label_en", "broader_concept")
    ordering = ["url"]
    filter_horizontal = ("broader",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("broader", "narrower")

    @admin.display(description="broader")
    def broader_concept(self, obj):
        return [parent.get_label() for parent in obj.broader.all()]

    @admin.display(
        description="pref_label",
        ordering=Case(  # allow sorting by label, prioritize English if available
            When(pref_label__en__isnull=False, then="pref_label__en"),
            default="pref_label__fi",
        ),
    )
    def label_en(self, obj):
        return obj.get_label()


for model in reference_data_models:
    admin.register(model)(AbstractConceptAdmin)
