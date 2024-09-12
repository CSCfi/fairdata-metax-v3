import copy
import json
import logging
import re
import uuid
from collections import Counter
from datetime import datetime
from typing import List, Optional, Tuple

from cachalot.api import cachalot_disabled
from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from model_utils import FieldTracker
from rest_framework import exceptions, serializers

from apps.common.helpers import ensure_dict
from apps.common.models import AbstractBaseModel
from apps.core.models import FileSet
from apps.core.models.catalog_record import DatasetPermissions
from apps.core.models.concepts import FileType, UseCategory
from apps.core.models.file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata
from apps.core.models.legacy_converter import LegacyDatasetConverter
from apps.files.models import File
from apps.users.models import MetaxUser

from .catalog_record import Dataset
from .preservation import Contract

logger = logging.getLogger(__name__)


class IncompatibleAPIVersion(exceptions.APIException):
    status_code = 400


def add_escapes(val: str):
    val = val.replace("[", "\\[")
    return val.replace("]", "\\]")


def regex(path: str):
    """Escape [ and ] and compile into regex."""
    return re.compile(add_escapes(path))


class LegacyDataset(AbstractBaseModel):
    """Legacy data for migrating V1 and V2 Datasets

    Stores legacy dataset json fields and creates or updates a corresponding v3 dataset
    when update_from_legacy is called.

    Attributes:
        dataset (models.OneToOneField): Migrated dataset
        dataset_json (models.JSONField): V1/V2 dataset json from legacy metax dataset API
        contract_json (models.JSONField): Contract json for which the dataset is under
        legacy_file_ids (models.ArrayField): List of V1/V2 file ids associated with the dataset
        v2_dataset_compatibility_diff (models.JSONField): Difference between v1-v2 and V3 dataset json
    """

    dataset = models.OneToOneField(Dataset, on_delete=models.CASCADE, null=True)
    dataset_json = models.JSONField(encoder=DjangoJSONEncoder)
    contract_json = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    legacy_file_ids = ArrayField(models.BigIntegerField(), null=True, blank=True)
    v2_dataset_compatibility_diff = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="Difference between v1-v2 and V3 dataset json",
    )
    migration_errors = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    last_successful_migration = models.DateTimeField(null=True, blank=True)
    invalid_legacy_values = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    fixed_legacy_values = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    tracker = FieldTracker()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_objects = Counter()

    @property
    def is_legacy(self):
        return True

    @property
    def legacy_identifier(self):
        """Legacy database primary key"""
        return self.dataset_json.get("identifier")

    @property
    def legacy_persistent_identifier(self):
        """Resolvable persistent identifier like DOI or URN"""
        return self.legacy_research_dataset.get("preferred_identifier")

    @property
    def metadata_provider_user(self):
        return self.dataset_json.get("metadata_provider_user")

    @property
    def metadata_provider_org(self):
        if org := self.dataset_json.get("metadata_provider_org"):
            return org
        else:
            return self.dataset_json.get("metadata_owner_org")

    @property
    def legacy_research_dataset(self):
        return ensure_dict(self.dataset_json.get("research_dataset") or {})

    @property
    def legacy_data_catalog(self):
        return self.dataset_json.get("data_catalog")

    @property
    def legacy_contract(self):
        if self.contract_json:
            return self.contract_json["contract_json"]

    def validate_identifiers(self):
        if not self.legacy_identifier:
            raise serializers.ValidationError(
                {"dataset_json__identifier": _("Value is required.")}
            )
        try:
            uuid.UUID(self.legacy_identifier)
        except ValueError:
            raise serializers.ValidationError(
                {"dataset_json__identifier": _("Value is not a valid UUID.")}
            )

    def attach_contract(self) -> Contract:
        if self.legacy_contract:
            ensure_dict(self.legacy_contract)
            contract, created = Contract.objects.get_or_create(
                quota=self.legacy_contract["quota"],
                valid_from=self.legacy_contract["validity"]["start_date"],
                description=self.legacy_contract["description"],
                title={"fi": self.legacy_contract["title"]},
                url=self.legacy_contract["identifier"],
            )
            if created:
                self.created_objects.update(["Contract"])
            self.dataset.contract = contract
            return contract

    def attach_files(self):
        skip = False
        legacy_file_ids = self.legacy_file_ids or []
        if not legacy_file_ids:
            skip = True

        fileset = getattr(self.dataset, "file_set", None)
        if (
            self.dataset.state == Dataset.StateChoices.PUBLISHED
            and fileset
            and fileset.total_files_count == len(legacy_file_ids)
        ):
            # Files are never completely removed from a published dataset so if the
            # file count matches, we have the correct files
            skip = True

        if not skip:
            found_files = File.all_objects.filter(legacy_id__in=legacy_file_ids).values_list(
                "id", flat=True
            )

            if missing_files_count := len(legacy_file_ids) - len(found_files):
                raise serializers.ValidationError(
                    {
                        "files": f"Missing files for dataset {self.dataset.id}: {missing_files_count}"
                    }
                )

            if not fileset:
                storage = File.all_objects.get(id=found_files[0]).storage
                fileset = FileSet.objects.create(dataset=self.dataset, storage_id=storage.id)
                self.created_objects.update(["FileSet"])

            logger.info(f"Assigning {len(found_files)} files to dataset {self.dataset.id}")
            fileset.files(manager="all_objects").set(found_files)
            fileset.clear_cached_file_properties()

        if fileset:
            self.attach_file_metadata(fileset)
            self.attach_directory_metadata(fileset)
            fileset.remove_unused_file_metadata()

    def get_refdata(self, model, entry: dict):
        if not entry:
            return
        if not hasattr(self, "_refdata_cache"):
            self._refdata_cache = {}

        identifier = entry["identifier"]
        if use_category := self._refdata_cache.get(identifier):
            return use_category

        converter = LegacyDatasetConverter(dataset_json={}, convert_only=False)
        instance, created = converter.get_or_create_reference_data(
            model,
            identifier,
            defaults={
                "pref_label": entry.get("pref_label"),
                "in_scheme": entry.get("in_scheme"),
                "deprecated": timezone.now(),
            },
        )
        if created:
            self.created_objects.update([model.__name__])
        return instance

    def attach_file_metadata(self, fileset: FileSet):
        files_metadata = copy.deepcopy(self.legacy_research_dataset.get("files")) or []
        files_metadata_ids = [f["details"]["id"] for f in files_metadata]

        file_ids = {  # Map legacy id to V3 id
            file["legacy_id"]: file["id"]
            for file in fileset.files(manager="all_objects")
            .filter(legacy_id__in=files_metadata_ids)
            .values("legacy_id", "id")
        }
        existing_metadata = {entry.file_id: entry for entry in fileset.file_metadata.all()}
        for fm in files_metadata:
            file_id = file_ids.get(fm.get("details", {})["id"])
            if not file_id:
                break
            existing = existing_metadata.get(file_id)

            file_type = self.get_refdata(FileType, fm.get("file_type"))
            use_category = self.get_refdata(UseCategory, fm.get("use_category"))
            if existing:
                existing.title = fm.get("title")
                existing.description = fm.get("description")
                existing.file_type = file_type
                existing.use_category = use_category
                existing.save()
                existing._found = True
            else:
                FileSetFileMetadata.objects.create(
                    file_set=fileset,
                    file_id=file_id,
                    title=fm.get("title"),
                    description=fm.get("description"),
                    file_type=file_type,
                    use_category=use_category,
                )
                self.created_objects.update(["FileSetFileMetadata"])
        # Delete metadata no longer in dataset
        fileset.file_metadata.filter(
            id__in=[m.id for m in existing_metadata.values() if not getattr(m, "_found", False)]
        ).delete()

    def attach_directory_metadata(self, fileset: FileSet):
        directories_metadata = copy.deepcopy(self.legacy_research_dataset.get("directories")) or []
        existing_metadata = {entry.pathname: entry for entry in fileset.directory_metadata.all()}
        for dm in directories_metadata:
            pathname: str = dm["details"]["directory_path"]
            if not pathname.endswith("/"):
                pathname += "/"

            existing = existing_metadata.get(pathname)
            use_category = self.get_refdata(UseCategory, dm.get("use_category"))
            if existing:
                existing.title = dm.get("title")
                existing.description = dm.get("description")
                existing.use_category = use_category
                existing.save()
                existing._found = True
            else:
                FileSetDirectoryMetadata.objects.create(
                    file_set=fileset,
                    storage=fileset.storage,
                    pathname=pathname,
                    title=dm.get("title"),
                    description=dm.get("description"),
                    use_category=use_category,
                )
                self.created_objects.update(["FileSetDirectoryMetadata"])
        # Delete metadata no longer in dataset
        fileset.directory_metadata.filter(
            id__in=[m.id for m in existing_metadata.values() if not getattr(m, "_found", False)]
        ).delete()

    def get_modified_editors(
        self, permissions: DatasetPermissions, editors: List[dict]
    ) -> Tuple[List[dict], Optional[datetime]]:
        """Return modified editors and latest modification timestamp."""
        latest_modified: Optional[datetime] = permissions.legacy_modified
        modified_editors = []
        for editor in editors:
            modified = parse_datetime(editor.get("date_modified") or editor.get("date_created"))
            if (not permissions.legacy_modified) or modified > permissions.legacy_modified:
                modified_editors.append(editor)
                if (not latest_modified) or modified > latest_modified:
                    latest_modified = modified
        return modified_editors, latest_modified

    def get_or_create_users(self, user_ids: List[str]) -> List[MetaxUser]:
        """Get users by username, create missing users."""
        existing = {
            user.username: user for user in MetaxUser.all_objects.filter(username__in=user_ids)
        }
        new = [MetaxUser(username=user_id) for user_id in user_ids if user_id not in existing]
        new = MetaxUser.all_objects.bulk_create(new)
        return [*existing.values(), *new]

    def update_permissions(self) -> Optional[str]:
        """Update changed DatasetPermissions.

        Returns:
            str or None: DatasetPermissions id that should be associated with the dataset.
        """
        perms_json = self.dataset_json.get("editor_permissions")
        if not perms_json:
            return None  # Value of dataset.permissions_id will be unchanged

        # Use same uuid for DatasetPermissions as in V2
        perms_id = perms_json["id"]
        perms, created = DatasetPermissions.all_objects.get_or_create(id=perms_id)

        # User with "creator" role is always metadata_owner_user in V2,
        # which is redundant so only users with "editor" role are relevant
        json_editors = [
            user for user in perms_json.get("users", []) if user.get("role") == "editor"
        ]
        if not json_editors:
            return str(perms_id)

        existing_editors = []
        if not created:
            existing_editors = perms.editors.values_list("username", flat=True)

        # Determine users that should be added or removed
        added = []
        removed = []
        modified_editors, latest_modification = self.get_modified_editors(perms, json_editors)
        for user in modified_editors:
            user_id = user["user_id"]
            if user.get("removed"):
                if user_id in existing_editors:
                    removed.append(user_id)
            else:
                if user_id not in existing_editors:
                    added.append(user_id)

        if added or removed:
            perms.legacy_modified = latest_modification
            perms.save()
            perms.editors.add(*self.get_or_create_users(added))
            perms.editors.remove(*MetaxUser.available_objects.filter(username__in=removed))
        return perms_id

    def attach_draft(self) -> Optional[str]:
        """Attach draft_of and next_draft values to dataset."""
        if draft_of := self.dataset_json.get("draft_of"):
            draft_of = Dataset.all_objects.filter(id=draft_of["identifier"]).first()
            if draft_of:  # Assign draft_of if dataset found
                self.dataset.draft_of = draft_of
                Dataset.all_objects.filter(id=self.dataset.id).update(draft_of=draft_of)
                logger.info(f"Assigned {draft_of.id} to draft_of for dataset {self.dataset.id} ")

        if next_draft := self.dataset_json.get("next_draft"):
            next_draft = Dataset.all_objects.filter(id=next_draft["identifier"]).first()
            if next_draft:  # Assign draft_of of the next_draft dataset if found
                Dataset.all_objects.filter(id=next_draft.id).update(draft_of=self.dataset)
                logger.info(
                    f"Assigned {next_draft.id} to next_draft for dataset {self.dataset.id} "
                )

    def update_from_legacy(self, context=None, raise_serializer_errors=True, create_files=False):
        """Update dataset fields from legacy data dictionaries."""
        if self._state.adding:
            raise ValueError("LegacyDataset needs to be saved before using update_from_legacy.")

        if not context:
            context = {}

        if self.dataset and self.dataset.api_version >= 3:
            raise IncompatibleAPIVersion(
                detail="Dataset has been modified with a later API version."
            )

        from apps.core.models.legacy_versions import get_or_create_dataset_versions
        from apps.core.serializers.legacy_serializer import LegacyDatasetUpdateSerializer

        is_creating_dataset = not self.dataset
        updated = False
        try:
            with transaction.atomic():  # Undo update if e.g. serialization fails
                converter = LegacyDatasetConverter(
                    dataset_json=self.dataset_json, convert_only=False
                )
                data = converter.convert_dataset()
                if perms_id := self.update_permissions():
                    data["permissions_id"] = perms_id
                self.created_objects.update(converter.created_objects)
                self.invalid_legacy_values = converter.get_invalid_values_by_path()
                self.fixed_legacy_values = converter.get_fixed_values_by_path()
                serializer = LegacyDatasetUpdateSerializer(
                    instance=self.dataset,
                    data=data,
                    context={**context, "dataset": self.dataset, "migrating": True},
                )
                serializer.is_valid(raise_exception=True)
                dataset_versions = get_or_create_dataset_versions(self)
                self.dataset = serializer.save(dataset_versions=dataset_versions)
                self.attach_draft()
                with cachalot_disabled():
                    self.attach_files()
                self.attach_contract()
                updated = True
        except serializers.ValidationError as error:
            # Save error details to migration_errors
            if is_creating_dataset:
                self.dataset = None  # Transaction failed and dataset was not created
            detail = error.detail
            if not isinstance(error.detail, list):
                detail = [detail]
            detail = json.loads(json.dumps(detail))
            self.migration_errors = {"serializer_errors": detail}
            LegacyDataset.all_objects.filter(id=self.id).update(
                migration_errors=self.migration_errors,
                invalid_legacy_values=self.invalid_legacy_values,
                fixed_legacy_values=self.fixed_legacy_values,
            )
            if raise_serializer_errors:
                raise
        if updated:
            from apps.core.models.legacy_compatibility import LegacyCompatibility

            compat = LegacyCompatibility(self)
            diff = compat.get_compatibility_diff()
            self.v2_dataset_compatibility_diff = diff
            if migration_errors := compat.get_migration_errors_from_diff(diff):
                self.migration_errors = migration_errors
            else:
                self.migration_errors = None
                self.last_successful_migration = timezone.now()

        self.save()
        return self

    def save(self, *args, **kwargs):
        self.validate_identifiers()

        self.id = self.legacy_identifier
        if Dataset.objects.filter(id=self.id, is_legacy=False).exists():
            raise serializers.ValidationError(
                {"id": _("A non-legacy dataset already exists with the same identifier.")}
            )

        if not self._state.adding:
            # Some fields (especially legacy_file_ids) may be big, update only if they have changed
            omit_fields = set()
            for field in ["legacy_file_ids", "dataset_json"]:
                if not self.tracker.has_changed(field):
                    omit_fields.add(field)

            if omit_fields:
                omit_fields.add("id")  # id can't be updated
                update_fields = kwargs.get("update_fields")
                if not update_fields:  # Get all updatable fields
                    update_fields = [
                        f.name
                        for f in (kwargs.get("update_fields") or self._meta.local_concrete_fields)
                    ]
                kwargs["update_fields"] = [f for f in update_fields if f not in omit_fields]

        super().save(*args, **kwargs)
