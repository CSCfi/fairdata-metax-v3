# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional

from django.db.models import F, prefetch_related_objects
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.settings import api_settings

from apps.common.helpers import get_technical_metax_user
from apps.common.serializers import StrictSerializer
from apps.files.models.file import File, FileCharacteristics, FileStorage
from apps.files.models.file_storage import FileStorage
from apps.files.serializers.file_serializer import FileSerializer
from apps.files.signals import pre_files_deleted


class PartialFileSerializer(FileSerializer):
    """File serializer that does not validate required fields.

    All fields have required=False and id is writable.
    Null id is treated as missing id.
    """

    class Meta(FileSerializer.Meta):
        extra_kwargs = {
            "id": {"read_only": False, "allow_null": True, "required": False},
            "pas_compatible_file": {"validators": []},  # Do validation in bulk
        }

    def to_internal_value(self, data):
        val = super().to_internal_value(data)
        if val.get("id") is None:
            val.pop("id", None)

        val["original_data"] = data  # retain original data for error reporting
        val["errors"] = {}  # store for validation errors
        return val


@dataclass
class BulkFileFail:
    object: dict
    errors: dict


class BulkAction(Enum):
    INSERT = "insert"
    UPDATE = "update"
    UPSERT = "upsert"
    DELETE = "delete"


class FileBulkSuccessSerializer(serializers.Serializer):
    object = PartialFileSerializer(help_text=_("Serialized file from database."))
    action = serializers.CharField()


class FileBulkFailSerializer(serializers.Serializer):
    object = serializers.JSONField(help_text=_("Failed input data."))
    errors = serializers.JSONField(help_text=_("Errors organized by input field."))


class FileBulkReturnValueSerializer(serializers.Serializer):
    success = FileBulkSuccessSerializer(many=True)
    failed = FileBulkFailSerializer(many=True)


class FileBulkSerializer(serializers.ListSerializer):
    """Serializer for bulk file creation.

    Action parameter should be one of BulkAction values:
    * insert: Create new files.
    * update: Update existing files.
    * upsert: Create new files or replace already existing files.
    * delete: Delete existing files.
    Update supports partial updating. Values omitted from the request are not changed.

    If input file has an id, it's treated as an existing file.
    If input file has a storage_identifier, its existence is checked from the database.
    If input file has no id and no storage_identifier, it's treated as a new file.

    Call serializer.save() to apply changes. After this,
    serializer.data will return an object in the format
    {
        "success": [
            { "object": { ... }, action: "insert" } ,
        ],
        "failed": [
            { "object": { ... }, errors: { ... } } ,
        ]
    }

    When ignore_errors is enabled (False by default), changes will be committed even if
    there are errors for some objects. Otherwise, only failed objects will be returned.

    Where success objects will contain the deserialized file object
    and failed objects will contain the corresponding input data.
    Order of input files is maintained so successes and failed objects
    are in the same order as in the request.
    """

    BULK_INSERT_ACTIONS = {BulkAction.INSERT, BulkAction.UPSERT}
    BULK_UPDATE_ACTIONS = {BulkAction.UPDATE, BulkAction.UPSERT}
    BULK_DELETE_ACTIONS = {BulkAction.DELETE}

    def __init__(self, *args, action: BulkAction, ignore_errors=False, **kwargs):
        self.action: BulkAction = action
        self.child = PartialFileSerializer(patch=action not in self.BULK_INSERT_ACTIONS)
        self.ignore_errors = ignore_errors
        super().__init__(*args, **kwargs)
        self.failed: List[BulkFileFail] = []

    def fail(self, object: dict, errors: dict):
        """Add object to list of failed items."""
        for key, error in errors.items():
            # simplify 1-length arrays from `[error]` to `error``
            if isinstance(error, list) and len(error) == 1:
                errors[key] = error[0]
        self.failed.append(BulkFileFail(object=object, errors=errors))

    @property
    def failed_as_dicts(self) -> List[dict]:
        return [asdict(fail) for fail in self.failed]

    def check_id_field_allowed(self, files: List[dict]) -> List[dict]:
        """Check that id field is allowed."""
        update_allowed = self.action in self.BULK_UPDATE_ACTIONS
        deleting = self.action in self.BULK_DELETE_ACTIONS
        if not (update_allowed or deleting):
            for file in files:
                if "id" in file:
                    file["errors"].setdefault("id", _("Field not allowed for inserting files."))
        return files

    def check_ids_exist(self, files: List[dict]) -> List[dict]:
        """Check that all file ids point to existing files."""
        data_ids = [f["id"] for f in files if "id" in f]
        existing_ids = set(File.objects.filter(id__in=data_ids).values_list("id", flat=True))

        for file in files:
            if "id" in file and file["id"] not in existing_ids:
                file["errors"].setdefault("id", _("File with id not found."))
        return files

    def group_files_by_storage_service(self, files: List[dict]) -> Dict[Optional[str], dict]:
        """Return files grouped by storage service."""
        files_by_service = {}
        for f in files:
            files_by_service.setdefault(f.get("storage_service"), []).append(f)
        return files_by_service

    def populate_id_from_external_identifier(self, files):
        """Add id value to files that already exist based on external id."""

        insert_allowed = self.action in self.BULK_INSERT_ACTIONS
        files_missing_id = [f for f in files if "id" not in f]
        for storage_service, storage_files in self.group_files_by_storage_service(
            files_missing_id
        ).items():
            if not storage_service:
                if not insert_allowed:
                    for f in storage_files:
                        f["errors"][
                            "storage_service"
                        ] = "Either storage_service or id is required."
                continue

            files_by_external_id = {}

            for f in storage_files:
                if external_id := f.get("storage_identifier"):
                    files_by_external_id.setdefault(external_id, []).append(f)
                elif not insert_allowed:
                    f["errors"][
                        "storage_identifier"
                    ] = "Either storage_identifier or id is required."

            # Get all files with matching external id
            existing_files = File.available_objects.filter(
                storage__storage_service=storage_service,
                storage_identifier__in=files_by_external_id.keys(),
            ).values(
                "storage_identifier",
                "id",
                csc_project=F("storage__csc_project"),
            )

            for existing_file in existing_files:
                for file in files_by_external_id[existing_file["storage_identifier"]]:
                    file["id"] = existing_file["id"]
                    # Project id can also be determined from external id when storage_service is known
                    if not file.get("csc_project"):
                        file["csc_project"] = existing_file["csc_project"]

        return files

    def check_duplicate_ids(self, files: List[dict]) -> List[dict]:
        """Check that same files are not being modified multiple times."""
        existing_files = [f for f in files if "id" in f]
        id_values = set()
        for f in existing_files:
            if f["id"] in id_values:
                f["errors"].setdefault("id", _("Duplicate file in request."))
            else:
                id_values.add(f["id"])
        return files

    def check_relations(self, files: List[dict]) -> List[dict]:
        """Validate pas_compatible_file relations."""
        files_with_pas = [f for f in files if f.get("pas_compatible_file")]
        if files_with_pas:
            # Map existing file.id -> file.pas_compatible_file.id relations
            pas_compatible = [f["pas_compatible_file"].id for f in files_with_pas]
            pas_relations = dict(
                File.all_objects.filter(
                    id__in=pas_compatible, non_pas_compatible_file__isnull=False
                ).values_list("non_pas_compatible_file", "id")
            )

            # Determine what the relations would look like after the update
            tmp_id_counter = 1
            for f in files_with_pas:
                _id = f.get("id")
                if _id is None:  # New files don't have id yet, use temporary int values in mapping
                    _id = tmp_id_counter
                    tmp_id_counter += 1
                pas_relations[_id] = f["pas_compatible_file"].id

            # Count how many pas_compatible_file relations point to each file
            counts = Counter(pas_relations.values())

            # Check the resulting relations
            for f in files_with_pas:
                if f["pas_compatible_file"].id == f.get("id"):
                    f["errors"]["pas_compatible_file"] = "File cannot refer to itself."
                elif counts[f["pas_compatible_file"].id] > 1:
                    f["errors"][
                        "pas_compatible_file"
                    ] = "File with this pas_compatible_file already exists."
        return files

    def check_creating_new_allowed(self, files: List[dict]) -> List[dict]:
        """Check if inserting new files is allowed."""
        insert_allowed = self.action in self.BULK_INSERT_ACTIONS
        if not insert_allowed:
            # All files should be existing and have an id
            for file in files:
                if "id" not in file and "id" not in file["errors"]:
                    file["errors"]["id"] = "File not found."
        return files

    def check_changing_existing_allowed(self, files: List[dict]) -> List[dict]:
        """Check if inserting new files is allowed."""
        update_allowed = self.action in self.BULK_UPDATE_ACTIONS
        deleting = self.action in self.BULK_DELETE_ACTIONS
        # User-provided id is only allowed when updating
        if not (update_allowed or deleting):
            # All files should be new and not have an existing id
            for file in files:
                if "id" in file and "id" not in file["errors"]:
                    file["errors"]["id"] = _("File already exists.")
        return files

    def check_files_allowed_actions(self, files: List[dict]) -> List[dict]:
        """Check that only allowed actions are performed on files.

        Files containing an id field are assumed to exist."""
        files = self.check_creating_new_allowed(files)
        files = self.check_changing_existing_allowed(files)
        return files

    def assign_existing_storage_data(self, files: List[dict]) -> List[dict]:
        """Assign storage and related fields to existing file data."""
        existing_files_with_missing_project_data = [
            f for f in files if "id" in f and not ("storage_service" in f and "csc_project" in f)
        ]
        project_data = File.objects.filter(
            id__in=[f["id"] for f in existing_files_with_missing_project_data]
        ).values(
            "id",
            storage_service=F("storage__storage_service"),
            csc_project=F("storage__csc_project"),
        )
        project_data_by_id = {f["id"]: f for f in project_data}

        # Don't overwrite existing input values so user later gets an
        # error if attempting to modify the values
        for f in existing_files_with_missing_project_data:
            if project_data := project_data_by_id.get(f["id"]):
                if f.get("storage_service") is None:
                    f["storage_service"] = project_data["storage_service"]
                if f.get("csc_project") is None:
                    f["csc_project"] = project_data["csc_project"]
        return files

    def assign_storage_to_files(self, files: List[dict]) -> List[dict]:
        """Assign FileStorage instances to files."""
        if not files:
            return files

        allow_create = self.action in self.BULK_INSERT_ACTIONS
        files = FileStorage.objects.assign_to_file_data(
            files, allow_create=allow_create, raise_exception=False
        )
        return files

    def flush_file_errors(self, files: List[dict]) -> List[dict]:
        """Remove errors field and return only files that have no errors."""
        ok_values = []
        for f in files:
            if errors := f.pop("errors"):
                # Add invalid files to self.failed
                self.fail(object=f["original_data"], errors=errors)
            else:
                ok_values.append(f)
        return ok_values

    def to_internal_value(self, data) -> List[dict]:
        # Deserialize data and run basic validation
        if not isinstance(data, list):
            msg = self.error_messages["not_a_list"].format(input_type=type(data).__name__)
            raise serializers.ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [msg]}, code="not_a_list"
            )

        files = []
        for item in data:
            try:
                validated = self.child.run_validation(item)
                files.append(validated)
            except serializers.ValidationError as exc:
                self.fail(object=item, errors=exc.detail)

        # Identifier checks
        files = self.check_id_field_allowed(files)
        files = self.check_ids_exist(files)

        files = self.populate_id_from_external_identifier(files)
        files = self.check_duplicate_ids(files)
        files = self.check_relations(files)

        # Checks for required and forbidden values
        files = self.check_files_allowed_actions(files)

        # Assign FileStorage and related values
        files = self.assign_existing_storage_data(files)
        files = self.assign_storage_to_files(files)

        # FileStorage-specific checks
        files = FileStorage.check_required_file_fields(files, raise_exception=False)
        files = FileStorage.check_file_data_conflicts(files, raise_exception=False)

        return self.flush_file_errors(files)

    def update_file_instance(self, instance, file_data) -> Optional[File]:
        """Update instance attributes of a File instance.

        Returns the updated file, or None if there were errors."""
        # store original data for error messages
        errors = {}
        for field, value in file_data.items():
            if field in FileSerializer.create_only_fields:
                existing_value = getattr(instance, field, None)
                if field == "storage":
                    existing_value = {"id": existing_value.id}
                if value != existing_value:
                    errors[field] = _("Cannot change value after creation")
            else:
                setattr(instance, field, value)  # assign new values
        if errors:
            self.fail(
                object=instance._original_data,
                errors=errors,
            )
            return None
        instance.record_modified = timezone.now()
        return instance

    def assign_characteristics(self, file: File, characteristics_data: Optional[dict]):
        """Assign characteristics data (not saved yet) to file."""
        if not characteristics_data:
            file.characteristics = None
            return
        if characteristics := file.characteristics:
            file.characteristics._changed = False
            for field, value in characteristics_data.items():
                if getattr(characteristics, field) != value:
                    file.characteristics._changed = True
                    setattr(characteristics, field, value)
        else:
            file.characteristics = FileCharacteristics(**characteristics_data)
            file.characteristics._changed = True

    def get_file_instances(self, validated_data) -> List[File]:
        """Return not yet saved instances from validated data."""
        system_creator = get_technical_metax_user()

        existing_files_by_id = (
            File.available_objects.prefetch_related("storage")
            .select_related("characteristics")
            .in_bulk([f["id"] for f in validated_data if "id" in f])
        )

        files = []
        for f in validated_data:
            characteristics_data = f.pop("characteristics", serializers.empty)
            if "id" not in f:  # new file
                # Note: To determine if a File instance is not yet in the DB,
                # use instance._state.adding. For a UUID-style id, the id is
                # set on instantiation instead of on save, so checking
                # `id is None` won't work.
                original_data = f.pop("original_data")
                f.pop("storage_service", None)  # included in FileStorage
                f.pop("csc_project", None)  # included in FileStorage
                file = File(**f, system_creator_id=system_creator)
                file._original_data = original_data
                files.append(file)
            else:  # existing file
                file = existing_files_by_id[f["id"]]
                file._original_data = f.pop("original_data")
                if self.action in self.BULK_UPDATE_ACTIONS:
                    file = self.update_file_instance(file, f)
                if file:
                    files.append(file)

            if file and characteristics_data is not serializers.empty:
                self.assign_characteristics(file, characteristics_data)
        return files

    def do_create_or_update(self, files: List[File]) -> List[dict]:
        """Perform bulk create and update actions for files."""
        fields_to_update = {
            field.name
            for field in File._meta.get_fields()
            if field.concrete and field.name not in {"id", *FileSerializer.create_only_fields}
        }
        characteristics_fields = [
            field.name
            for field in FileCharacteristics._meta.get_fields()
            if field.concrete and field.name != "id"
        ]

        # Create or update files and characteristics
        changed_characteristics = [
            file.characteristics
            for file in files
            if file.characteristics and getattr(file.characteristics, "_changed", False)
        ]
        FileCharacteristics.objects.bulk_create(
            changed_characteristics,
            batch_size=5000,
            update_conflicts=True,  # Update characteristics that already exist
            unique_fields=["id"],
            update_fields=characteristics_fields,
        )

        being_created = {f.id for f in files if f._state.adding}
        files = File.objects.bulk_create(
            files,
            batch_size=5000,
            update_conflicts=True,  # Update files that already exist
            unique_fields=["id"],
            update_fields=fields_to_update,
        )
        # Related objects need to be fetched again from DB after save
        prefetch_related_objects(files, "storage", "characteristics")

        # Cleanup any orphaned characteristics
        FileCharacteristics.objects.filter(file__isnull=True).delete()

        def file_action(file):
            if file.id in being_created:
                return BulkAction.INSERT
            else:
                return BulkAction.UPDATE

        return [
            {
                "object": f,
                "action": file_action(f).value,
            }
            for f in files
        ]

    def do_delete(self, files: List[File]) -> List[dict]:
        """Perform bulk delete on files."""
        now = timezone.now()
        for f in files:
            f.removed = now  # include new value in response

        # Update all files in db at once
        file_ids = [f.id for f in files]
        files_to_delete = File.objects.filter(id__in=file_ids)
        pre_files_deleted.send(sender=File, queryset=files_to_delete)  # Deprecate datasets
        files_to_delete.update(removed=now)

        return [
            {
                "object": f,
                "action": "delete",
            }
            for f in files
        ]

    def create(self, validated_data):
        """Perform bulk file action.

        Returns success objects which will be stored in self.instance by .save()."""
        if len(validated_data) == 0:
            return []

        files = self.get_file_instances(validated_data)

        # Return empty success list on error
        if not self.ignore_errors and self.failed:
            return []

        success_files: List[dict]
        is_insert = self.action in self.BULK_INSERT_ACTIONS
        is_update = self.action in self.BULK_UPDATE_ACTIONS
        if is_insert or is_update:
            success_files = self.do_create_or_update(files)
        elif self.action in self.BULK_DELETE_ACTIONS:
            success_files = self.do_delete(files)

        return success_files

    def to_representation(self, instance):
        return FileBulkReturnValueSerializer(
            {"success": instance, "failed": self.failed_as_dicts}
        ).data

    @property
    def data(self):
        """Skip ListSerializer.data that tries to return list."""
        return super(serializers.ListSerializer, self).data
