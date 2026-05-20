import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.widgets import AutocompleteSelect
from django.db import models, transaction
from django.db.models.functions import Cast, Substr
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django_json_widget.widgets import JSONEditorWidget
from simple_history.admin import SimpleHistoryAdmin

from apps.common.admin import AbstractDatasetPropertyBaseAdmin, CommonAdmin

# Register your models here.
from apps.common.tasks import run_task
from apps.core.models import (
    AccessRights,
    CatalogHomePage,
    Contract,
    DataCatalog,
    Dataset,
    DatasetActor,
    DatasetLicense,
    DatasetProject,
    DatasetPublisher,
    Entity,
    EntityRelation,
    FieldOfScience,
    FileSet,
    Funding,
    GeoLocation,
    Language,
    LegacyDataset,
    MetadataProvider,
    OtherIdentifier,
    Provenance,
    RestrictionGrounds,
    Spatial,
    Temporal,
    Theme,
)
from apps.core.models.catalog_record.dataset import REMSStatus
from apps.core.models.preservation import Preservation
from apps.core.models.sync import SyncAction, V2SyncStatus
from apps.core.signals import sync_dataset_to_rems, sync_dataset_to_v2
from apps.rems.models import REMSCatalogueItem
from apps.users.models import MetaxUser

logger = logging.getLogger(__name__)


@admin.register(CatalogHomePage)
class CatalogHomePageAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(DatasetPublisher)
class DatasetPublisherAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(AccessRights)
class AccessRightsAdmin(AbstractDatasetPropertyBaseAdmin):
    list_filter = ["created", "modified", "access_type", "restriction_grounds"]
    list_display = ["dataset", "access_type", "description"]
    autocomplete_fields = ["license"]
    list_select_related = ("dataset", "access_type")
    search_fields = ["dataset__id", "description__values", "access_type__pref_label__values"]


@admin.register(DataCatalog)
class DataCatalogAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    list_display = (
        "id",
        "dataset_versioning_enabled",
        "is_external",
    )
    list_filter = (
        "dataset_versioning_enabled",
        "is_external",
        "created",
        "modified",
    )
    autocomplete_fields = ("language",)


@admin.register(MetadataProvider)
class MetadataProviderAdmin(CommonAdmin):
    list_display = ("user", "organization", "admin_organization")
    list_filter = ("created", "modified")
    search_fields = ("organization", "user__username", "user__email")
    readonly_fields = ["user", "organization", "admin_organization"]


class CoreRefDataAdminMixin:
    search_fields = ["pref_label__values", "url"]
    readonly_fields = ["broader"]
    list_filter = ("created", "modified")


@admin.register(Language)
class DatasetLanguage(CoreRefDataAdminMixin, CommonAdmin):
    pass


@admin.register(Theme)
class DatasetTheme(CoreRefDataAdminMixin, CommonAdmin):
    pass


@admin.register(FieldOfScience)
class DatasetFieldOfScience(CoreRefDataAdminMixin, CommonAdmin):
    pass


@admin.register(Funding)
class Funding(CommonAdmin):
    search_fields = ["funding_identifier"]
    list_filter = ("created", "modified")
    readonly_fields = ("funder",)


@admin.register(RestrictionGrounds)
class RestrictionGrounds(CoreRefDataAdminMixin, CommonAdmin):
    pass


class V2SyncStatusInline(admin.StackedInline):
    model = V2SyncStatus
    readonly_fields = (
        "sync_started",
        "sync_files_started",
        "sync_stopped",
        "duration",
        "action",
        "error",
    )


class REMSStatusFilter(admin.SimpleListFilter):
    title = "REMS state"
    parameter_name = "rems_status"

    def lookups(self, request, model_admin):
        return REMSStatus.choices

    def queryset(self, request, queryset):
        rems_datasets = queryset.rems_datasets()

        value = self.value()
        if value == REMSStatus.NOT_REMS:
            return queryset.exclude(id__in=rems_datasets)
        if value == REMSStatus.ERROR:
            return rems_datasets.filter(rems_publish_error__isnull=False)

        in_rems_ids = REMSCatalogueItem.objects.filter(key__startswith="dataset-").values_list(
            Cast(Substr("key", len("dataset-") + 1), output_field=models.UUIDField()), flat=True
        )
        if value == REMSStatus.PUBLISHED:
            return rems_datasets.filter(rems_publish_error__isnull=True).filter(id__in=in_rems_ids)
        if value == REMSStatus.NOT_PUBLISHED:
            return rems_datasets.filter(rems_publish_error__isnull=True).exclude(
                id__in=in_rems_ids
            )
        if value is not None:
            raise ValueError(f"Invalid REMSStatus {value=}")


class UpdateOwnerForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)

    user = forms.ModelChoiceField(
        queryset=MetaxUser.objects.all(),
        widget=AutocompleteSelect(
            MetadataProvider.user.field,
            admin.site,
        ),
        required=False,
    )
    organization = forms.CharField(required=False)
    admin_organization = forms.CharField(required=False)
    clear_admin_organization = forms.BooleanField(required=False)


class DatasetAdminForm(forms.ModelForm):
    """Dataset Admin form that exposes metadata owner fields."""

    metadata_owner_user = forms.ModelChoiceField(
        queryset=MetaxUser.objects.all(),
        widget=AutocompleteSelect(
            MetadataProvider.user.field,
            admin.site,
        ),
    )
    metadata_owner_organization = forms.CharField()
    metadata_owner_admin_organization = forms.CharField(required=False)

    class Meta:
        model = Dataset
        fields = "__all__"
        exclude = ("metadata_owner",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate initial values if editing existing instance
        if self.instance:
            self.initial.update(
                metadata_owner_user=self.instance.metadata_owner.user,
                metadata_owner_organization=self.instance.metadata_owner.organization,
                metadata_owner_admin_organization=self.instance.metadata_owner.admin_organization,
            )

    def save(self, commit=True):
        dataset = super().save(commit=False)

        # Get or create metadata owner matching the field values, assign to dataset
        metadata_owner_user = self.cleaned_data["metadata_owner_user"]
        metadata_owner_organization = self.cleaned_data["metadata_owner_organization"]
        metadata_owner_admin_organization = (
            self.cleaned_data["metadata_owner_admin_organization"] or None
        )
        owner = dataset.metadata_owner.reassign(
            user=metadata_owner_user,
            organization=metadata_owner_organization,
            admin_organization=metadata_owner_admin_organization,
        )
        dataset.metadata_owner = owner
        if commit:
            dataset.save()
        return dataset


@admin.register(Dataset)
class DatasetAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    form = DatasetAdminForm

    list_display = (
        "title",
        "access_rights",
        "deprecated",
        "state",
        "data_catalog",
        "created",
        "modified",
    )
    list_filter = (
        "created",
        "modified",
        "issued",
        "deprecated",
        "state",
        REMSStatusFilter,
        "data_catalog",
    )

    exclude = ("metadata_owner",)
    autocomplete_fields = ["language", "theme", "field_of_science"]
    readonly_fields = (
        "preservation",
        "dataset_versions",
        "other_identifiers",
        "last_modified_by",
        "access_rights",
        "draft_of",
        "permissions",
        "rems_status",
        "rems_check",
        "rems_publish_error",
    )
    list_select_related = ("access_rights", "data_catalog", "metadata_owner")
    search_fields = ["id", "persistent_identifier", "title__values", "keyword"]
    inlines = [V2SyncStatusInline]
    actions = ["sync_to_v2", "publish_to_rems", "update_owner"]

    def get_fieldsets(self, request, obj=None):
        """Organize fields into groups."""
        owner_fields = (
            "metadata_owner_user",
            "metadata_owner_organization",
            "metadata_owner_admin_organization",
        )
        rems_fields = (
            "rems_status",
            "rems_check",
            "rems_publish_error",
        )

        # Get all admin fields for the model
        all_fields = self.get_fields(request, obj)

        # Compute remaining fields
        used_fields = set(owner_fields) | set(rems_fields)
        remaining_fields = [f for f in all_fields if f not in used_fields]

        return (
            (
                "Metadata owner",
                {
                    "fields": owner_fields,
                },
            ),
            (
                "Dataset",
                {
                    "fields": remaining_fields,
                },
            ),
            (
                "REMS information",
                {
                    "fields": rems_fields,
                },
            ),
        )

    def get_fields(self, request, obj=...):
        fields = super().get_fields(request, obj)
        if not settings.REMS_ENABLED:
            fields = [f for f in fields if f != "rems_status"]
        return fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not settings.METAX_V2_INTEGRATION_ENABLED:
            actions.pop("sync_to_v2", None)
        if not settings.REMS_ENABLED:
            actions.pop("publish_to_rems", None)
        return actions

    @admin.action(description="Sync datasets to V2", permissions=["change"])
    def sync_to_v2(self, request, queryset):
        datasets = Dataset.objects.filter(id__in=[item.id for item in queryset])
        datasets.prefetch_related(*Dataset.common_prefetch_fields)
        for dataset in datasets:
            run_task(sync_dataset_to_v2, dataset=dataset, action=SyncAction.UPDATE)
            self.message_user(
                request,
                f"{len(datasets)} datasets set to sync to V2",
                messages.SUCCESS,
            )

    @admin.action(description="Publish to REMS", permissions=["change"])
    def publish_to_rems(self, request, queryset):
        datasets = Dataset.objects.filter(id__in=[item.id for item in queryset])
        not_rems = 0
        success = 0
        errors = 0
        for dataset in datasets:
            sync = sync_dataset_to_rems(dataset)
            if sync is None:
                not_rems += 1
            elif sync:
                success += 1
            else:
                errors += 1
        self.message_user(
            request,
            f"Publish to REMS: {success=} {errors=} {not_rems=}",
            messages.SUCCESS,
        )

    @admin.action(description="Update owner of selected datasets", permissions=["change"])
    @transaction.atomic
    def update_owner(self, request, queryset):
        if request.POST.get("apply"):
            # Apply new values for datasets metadata owners
            form = UpdateOwnerForm(request.POST)
            if form.is_valid():
                new_values = {}
                for field in ["user", "organization", "admin_organization"]:
                    if value := form.cleaned_data.get(field):
                        new_values[field] = value
                if form.cleaned_data.get("clear_admin_organization"):
                    new_values["admin_organization"] = None

                changed, total = self._update_dataset_owners(queryset, new_values)
                self.message_user(
                    request,
                    f"{changed} datasets updated out of {total} selected.",
                    messages.SUCCESS,
                )
                return redirect(request.get_full_path())

        # Render table of current values and form for new values
        form = UpdateOwnerForm(initial={"_selected_action": queryset.values_list("id", flat=True)})
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "objects": queryset,
            "form": form,
            "title": "Update dataset owner",
        }

        return TemplateResponse(
            request,
            "admin/update_dataset_owner.html",
            context,
        )

    def _update_dataset_owners(self, queryset, new_values) -> tuple[int, int]:
        """Assign new metadata owner values to datasets."""
        changed_datasets = []
        if new_values:
            for dataset in queryset:
                new_owner = dataset.metadata_owner.reassign(**new_values)
                if new_owner != dataset.metadata_owner:
                    dataset.metadata_owner = new_owner
                    changed_datasets.append(dataset)
                    dataset.save()

        for dataset in changed_datasets:
            dataset.signal_update()

        changed = len(changed_datasets)
        total = len(queryset)
        return changed, total


    def save_model(self, request, obj: Dataset, form, change):
        created = obj._state.adding
        super().save_model(request, obj, form, change)
        obj.update_index()
        obj.signal_update(created=created)


@admin.register(DatasetActor)
class DatasetActorAdmin(CommonAdmin):
    list_display = (
        "dataset",
        "actor",
        "roles",
    )
    list_filter = ("created", "modified")
    list_select_related = ("dataset",)
    autocomplete_fields = ["person", "organization", "dataset"]
    search_fields = (
        "dataset__id",
        "person__name",
        "person__email",
        "roles",
        "organization__pref_label__values",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("person", "organization", "dataset")

    def roles(self, obj):
        return ", ".join(o.name for o in obj.roles.all())

    def actor(self, obj):
        if obj.person:
            return str(obj.person)
        elif obj.organization:
            return str(obj.organization)
        else:
            return "none"


@admin.register(Preservation)
class PreservationAdmin(CommonAdmin):
    list_display = ("id", "dataset", "state", "pas_process_running")
    list_filter = ("state", "pas_process_running")
    search_fields = ("dataset__id",)
    readonly_fields = ("dataset",)


@admin.register(Temporal)
class TemporalAdmin(CommonAdmin):
    list_display = ("id", "start_date", "end_date", "dataset", "provenance")
    list_filter = ("created", "modified", "start_date", "end_date")
    search_fields = ("dataset__id", "provenance__id")
    readonly_fields = ("dataset", "provenance")


@admin.register(Provenance)
class ProvenanceAdmin(CommonAdmin):
    list_display = ("id", "title", "description")
    list_filter = ["created", "modified", "event_outcome", "lifecycle_event", "preservation_event"]
    autocomplete_fields = ["is_associated_with", "spatial"]
    search_fields = ("title__values", "dataset__id")
    readonly_fields = ("dataset",)


@admin.register(Spatial)
class SpatialAdmin(CommonAdmin):
    list_display = ("id", "full_address", "geographic_name", "dataset")
    search_fields = ["dataset__id", "full_address", "geographic_name"]
    list_filter = ("created", "modified", "geographic_name")
    readonly_fields = ("reference", "dataset")


@admin.register(OtherIdentifier)
class OtherIdentifierAdmin(CommonAdmin):
    list_display = ("notation",)
    list_filter = ("identifier_type", "created", "modified")


@admin.register(DatasetProject)
class DatasetProjectAdmin(CommonAdmin):
    list_display = ("title", "dataset")
    list_filter = ("created", "modified")
    search_fields = ["dataset__id", "title", "project_identifier"]
    autocomplete_fields = ["participating_organizations", "funding"]


@admin.register(LegacyDataset)
class LegacyDatasetAdmin(CommonAdmin):
    fields = (
        "id",
        "created",
        "modified",
        "dataset_json",
        "contract_json",
        "v2_dataset_compatibility_diff",
        "last_successful_migration",
    )
    readonly_fields = (
        "id",
        "created",
        "modified",
        "v2_dataset_compatibility_diff",
        "last_successful_migration",
    )
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}


@admin.register(Contract)
class ContractAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "title",
        "quota",
    )
    list_filter = ("validity_end_date", "created", "modified")


@admin.register(DatasetLicense)
class LicenseAdmin(AbstractDatasetPropertyBaseAdmin):
    search_fields = ["title__values", "id", "description__values"]
    list_filter = ["reference"]


class EntityInline(admin.TabularInline):
    model = EntityRelation


@admin.register(Entity)
class EntityRelationAdmin(AbstractDatasetPropertyBaseAdmin):
    inlines = [EntityInline]
    list_filter = ("type", "created", "modified")
    autocomplete_fields = ("provenance",)


@admin.register(FileSet)
class FileSetAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(V2SyncStatus)
class V2SyncStatusAdmin(CommonAdmin):
    readonly_fields = (
        "dataset",
        "sync_started",
        "sync_files_started",
        "sync_stopped",
        "duration",
        "action",
        "error",
    )
    list_display = (
        "dataset_id",
        "action",
        "sync_started",
        "sync_stopped",
        "duration",
        "status",
    )
    list_filter = ("sync_stopped",)
    actions = ["sync_to_v2"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not settings.METAX_V2_INTEGRATION_ENABLED:
            actions.pop("sync_to_v2", None)
        return actions

    @admin.action(description="Sync to V2", permissions=["change"])
    def sync_to_v2(self, request, queryset):
        V2SyncStatus.prefetch_datasets(queryset)
        for status in queryset:
            dataset: Dataset
            try:
                dataset = status.dataset
            except Dataset.DoesNotExist:
                if status.action == SyncAction.DELETE or status.action == SyncAction.FLUSH:
                    dataset = Dataset(id=status.dataset_id)
                else:
                    self.message_user(
                        request,
                        f"Dataset {status.dataset_id} not found",
                        messages.ERROR,
                    )
            run_task(sync_dataset_to_v2, dataset=dataset, action=status.action)
        self.message_user(
            request,
            f"{len(queryset)} datasets set to sync to V2",
            messages.SUCCESS,
        )


@admin.register(GeoLocation)
class GeoLocationAdmin(CommonAdmin):
    pass
