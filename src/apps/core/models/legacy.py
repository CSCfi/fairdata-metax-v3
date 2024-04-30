import json
import logging
import re
import uuid
from collections import Counter
from typing import Optional

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import exceptions, serializers

from apps.actors.models import Actor
from apps.common.helpers import ensure_dict, ensure_list, is_field_value_provided
from apps.core.models import FileSet
from apps.core.models.legacy_converter import LegacyDatasetConverter
from apps.files.models import File
from apps.files.serializers.file_serializer import get_or_create_storage
from apps.users.models import MetaxUser

from .catalog_record import Dataset, MetadataProvider
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


class LegacyDataset(Dataset):
    """Migrated V1 and V2 Datasets

    Stores legacy dataset json fields and derives v3 dataset
    fields from them when update_from_legacy is called.

    Attributes:
        dataset_json (models.JSONField): V1/V2 dataset json from legacy metax dataset API
        contract_json (models.JSONField): Contract json for which the dataset is under
        files_json (models.JSONField): Files attached to the dataset trough dataset/files API in v2
        v2_dataset_compatibility_diff (models.JSONField):
            Difference between v1-v2 and V3 dataset json
    """

    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )
    dataset_json = models.JSONField(encoder=DjangoJSONEncoder)
    contract_json = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    files_json = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_objects = Counter()

        # If api_version was not provided, replace the field default with value from dataset_json
        if not is_field_value_provided(self.__class__, "api_version", args, kwargs):
            self.api_version = self.dataset_json.get("api_meta", {}).get("version", 1)

        # Get minimal dataset fields from legacy json
        if not is_field_value_provided(self.__class__, "metadata_owner_id", args, kwargs):
            self.attach_metadata_owner()
        if "title" not in kwargs:
            self.title = self.legacy_research_dataset["title"]

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

    def create_snapshot(self, **kwargs):
        """Create snapshot of dataset.

        Due to how simple-history works, LegacyDataset will need to be "cast"
        into a normal Dataset for creating a snapshot.
        """
        self.dataset.create_snapshot(**kwargs)

    def convert_checksum_v2_to_v3(self, checksum: dict, value_key="value") -> Optional[str]:
        if not checksum:
            return None
        ensure_dict(checksum)
        algorithm = checksum.get("algorithm", "").lower().replace("-", "")
        value = checksum.get(value_key, "").lower()
        return f"{algorithm}:{value}"

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

    def attach_metadata_owner(self) -> Actor:
        """Creates new MetadataProvider object from metadata-owner field, that is usually CSC-username"""
        metadata_user, user_created = MetaxUser.objects.get_or_create(
            username=self.metadata_provider_user
        )
        owner_created = False
        metadata_owner = MetadataProvider.objects.filter(
            user=metadata_user, organization=self.metadata_provider_org
        ).first()
        if not metadata_owner:
            metadata_owner = MetadataProvider.objects.create(
                user=metadata_user, organization=self.metadata_provider_org
            )
            owner_created = True
        if owner_created:
            self.created_objects.update(["MetadataProvider"])
        if user_created:
            self.created_objects.update(["User"])
        self.metadata_owner = metadata_owner
        return metadata_owner

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
            self.contract = contract
            return contract

    def attach_files(self):
        storage_file_objects = {}
        if files := self.files_json:
            ensure_list(files)
            for f in files:
                file_id = f["identifier"]
                checksum = f.get("checksum", {})

                storage_service = settings.LEGACY_FILE_STORAGE_TO_V3_STORAGE_SERVICE[
                    f["file_storage"]["identifier"]
                ]
                storage = get_or_create_storage(
                    csc_project=f["project_identifier"],
                    storage_service=storage_service,
                )
                new_file, created = File.objects.get_or_create(
                    storage_identifier=file_id,
                    defaults={
                        "checksum": self.convert_checksum_v2_to_v3(checksum),
                        "size": f["byte_size"],
                        "pathname": f["file_path"],
                        "modified": f["file_modified"],
                        "storage_identifier": f["identifier"],
                        "storage": storage,
                    },
                )
                if created:
                    self.created_objects.update(["File"])

                storage_file_objects.setdefault(storage.id, []).append(new_file)

        file_set = None
        for storage_id, file_objects in storage_file_objects.items():
            file_set, created = FileSet.objects.get_or_create(dataset=self, storage_id=storage_id)
            if created:
                self.created_objects.update(["FileSet"])
            file_set.files.set(file_objects)
        return file_set

    def update_from_legacy(self, context=None, raise_serializer_errors=True):
        """Update dataset fields from legacy data dictionaries."""
        if self._state.adding:
            raise ValueError("LegacyDataset needs to be saved before using update_from_legacy.")

        if not context:
            context = {}

        if self.api_version >= 3:
            raise IncompatibleAPIVersion(
                detail="Dataset has been modified with a later API version."
            )

        from apps.core.serializers.legacy_serializer import LegacyDatasetUpdateSerializer

        updated = False
        try:
            with transaction.atomic():  # Undo update if e.g. serialization fails
                self.attach_metadata_owner()
                converter = LegacyDatasetConverter(
                    dataset_json=self.dataset_json, convert_only=False
                )
                data = converter.convert_dataset()
                self.created_objects.update(converter.created_objects)
                self.invalid_legacy_values = converter.get_invalid_values_by_path()
                self.fixed_legacy_values = converter.get_fixed_values_by_path()
                serializer = LegacyDatasetUpdateSerializer(
                    instance=self,
                    data=data,
                    context={**context, "dataset": self, "migrating": True},
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
                self.attach_files()
                self.attach_contract()
                updated = True
        except serializers.ValidationError as error:
            # Save error details to migration_errors
            detail = error.detail
            if not isinstance(error.detail, list):
                detail = [detail]
            detail = json.loads(json.dumps(detail))
            self.migration_errors = {"serializer_errors": detail}
            self.save()
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
        if str(self.id) != str(self.legacy_identifier):
            raise serializers.ValidationError({"id": _("Value does not match V2 identifier.")})

        self.validate_identifiers()

        if Dataset.objects.filter(id=self.id, legacydataset__isnull=True).exists():
            raise serializers.ValidationError(
                {"id": _("A non-legacy dataset already exists with the same identifier.")}
            )

        self.saving_legacy = True  # Enable less strict validation in Dataset.save
        return super().save(*args, **kwargs)
