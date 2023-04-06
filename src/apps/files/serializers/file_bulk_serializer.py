# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, NewType, Optional

from django.db.models import F
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.settings import api_settings

from apps.common.helpers import get_technical_metax_user
from apps.files.models.file import File, StorageProject
from apps.files.models.file_storage import FileStorage

from .file_serializer import FileSerializer


class PartialFileSerializer(FileSerializer):
    """File serializer that does not validate required fields.

    All fields have required=False and id is writable.
    Null id is treated as missing id.
    """

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.required = False
        return fields

    class Meta(FileSerializer.Meta):
        extra_kwargs = {
            "id": {"read_only": False, "allow_null": True},
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
    * upsert: Create new files or update already existing files.
    * delete: Delete existing files.
    Update support partial updating. Values omitted from the request are not changed.

    If input file has an id, it's treated as an existing file.
    If input file has an TODO:external_id, its existence is checked from the database.
    If input file has no id and no TODO:external_id, it's treated as a new file.

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

    Where success objects will contain the deserialized file object
    and failed objects will contain the corresponding input data.
    Order of input files is maintained so successes and failed objects
    are in the same order as in the request.
    """

    BULK_INSERT_ACTIONS = {BulkAction.INSERT, BulkAction.UPSERT}
    BULK_UPDATE_ACTIONS = {BulkAction.UPDATE, BulkAction.UPSERT}
    BULK_DELETE_ACTIONS = {BulkAction.DELETE}

    def __init__(self, *args, action: BulkAction, **kwargs):
        self.child = PartialFileSerializer()
        super().__init__(*args, **kwargs)
        self.action: BulkAction = action
        self.failed: List[BulkFileFail] = []

    def fail(self, object: dict, errors: dict):
        """Add object to list of failed items."""
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
                if "id" in file and "id" not in file["errors"]:
                    file["errors"]["id"] = _("Field not allowed for inserting files.")
        return files

    def check_ids_exist(self, files: List[dict]) -> List[dict]:
        """Check that all file ids point to existing files."""
        data_ids = [f["id"] for f in files if "id" in f]
        existing_ids = set(File.objects.filter(id__in=data_ids).values_list("id", flat=True))

        for file in files:
            if "id" in file and file["id"] not in existing_ids:
                if "id" not in file["errors"]:
                    file["errors"]["id"] = _("File with id not found.")
        return files

    def check_duplicate_ids(self, files: List[dict]) -> List[dict]:
        """Check that same files are not being modified multiple times."""
        existing_files = [f for f in files if "id" in f]
        id_values = set()
        for f in existing_files:
            if f["id"] in id_values:
                if "id" not in f["errors"]:
                    f["errors"]["id"] = _("Duplicate file id in request.")
            else:
                id_values.add(f["id"])
        return files

    def check_creating_new_allowed(self, files: List[dict]) -> List[dict]:
        """Check if inserting new files is allowed."""
        insert_allowed = self.action in self.BULK_INSERT_ACTIONS
        if not insert_allowed:
            # All files should be existing and have an id
            for file in files:
                if "id" not in file and "id" not in file["errors"]:
                    file["errors"]["id"] = _("Expected an existing file.")
        return files

    def check_changing_existing_allowed(self, files: List[dict]) -> List[dict]:
        """Check if inserting new files is allowed."""
        update_allowed = self.action in self.BULK_UPDATE_ACTIONS
        deleting = self.action in self.BULK_DELETE_ACTIONS
        # TODO: This is redundant until alternate identifier is supported
        # since user-provided id is only allowed when updating
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

    def check_new_files_required_fields(self, files: List[dict]) -> List[dict]:
        """Check that new files (no id) have all required fields."""
        required_fields = {
            name for name, field in FileSerializer().fields.items() if field.required
        }
        for f in files:
            if "id" not in f:  # new file
                missing_fields = required_fields - set(f)
                if missing_fields:
                    for field in missing_fields:
                        if field not in f["errors"]:
                            f["errors"][field] = _("Field is required for new files.")
        return files

    def assign_existing_project_data(self, files: List[dict]) -> List[dict]:
        """Assign file_storage and project_identifier to existing file data."""
        existing_files_with_missing_project_data = [
            f
            for f in files
            if "id" in f and not ("file_storage" in f and "project_identifier" in f)
        ]
        project_data = File.objects.filter(
            id__in=[f["id"] for f in existing_files_with_missing_project_data]
        ).values(
            "id",
            file_storage=F("storage_project__file_storage_id"),
            project_identifier=F("storage_project__project_identifier"),
        )
        project_data_by_id = {f["id"]: f for f in project_data}

        # Don't overwrite existing input values so user later gets an
        # error if attempting to modify the values
        for f in existing_files_with_missing_project_data:
            if project_data := project_data_by_id.get(f["id"]):
                if "file_storage" not in f:
                    f["file_storage"] = {"id": project_data["file_storage"]}
                if "project_identifier" not in f:
                    f["project_identifier"] = project_data["project_identifier"]
        return files

    def get_or_create_storage_projects_by_key_for_files(
        self, files: List[dict]
    ) -> Dict[tuple, StorageProject]:
        # Get StorageProjects for existing files
        data_ids = [f["id"] for f in files if "id" in f]
        storage_projects = StorageProject.objects.filter(files__in=data_ids)
        storage_projects_by_key = {
            (sp.file_storage_id, sp.project_identifier): sp for sp in storage_projects
        }

        # Get (or create) StorageProjects for new files
        storage_projects_errors_by_key = {}
        new_files = [f for f in files if "id" not in f]
        for f in new_files:
            if f["errors"]:
                continue  # Don't create StorageProject for files that have errors

            file_storage = f.get("file_storage")
            project_identifier = f.get("project_identifier")
            key = (file_storage["id"], project_identifier)
            if key not in storage_projects_by_key:
                try:
                    file_storage = FileStorage.available_objects.get(id=f["file_storage"]["id"])
                    storage_project, created = StorageProject.available_objects.get_or_create(
                        project_identifier=f["project_identifier"],
                        file_storage=file_storage,
                    )
                    storage_projects_by_key[key] = storage_project
                except FileStorage.DoesNotExist:
                    storage_projects_by_key[key] = None
                    storage_projects_errors_by_key[key] = {
                        "file_storage": _("File storage not found.")
                    }
            if errors := storage_projects_errors_by_key.get(key):
                f["errors"].update(**errors)
        return storage_projects_by_key

    def assign_storage_project_to_files(self, files: List[dict]) -> List[dict]:
        """Assign StorageProject instances to all files."""
        if not files:
            return files

        storage_projects_by_key = self.get_or_create_storage_projects_by_key_for_files(files)

        # Assign storage_project to files, may be None if there are errors
        for f in files:
            if "file_storage" in f and "project_identifier" in f:
                key = (f["file_storage"]["id"], f["project_identifier"])
                f["storage_project"] = storage_projects_by_key.get(key)
            else:
                f["storage_project"] = None
        return files

    def group_files_by_storage_project(self, files: List[dict]) -> Dict[StorageProject, dict]:
        files_by_project = {}
        for f in files:
            if f["storage_project"] not in files_by_project:
                files_by_project[f["storage_project"]] = []
            files_by_project[f["storage_project"]].append(f)
        return files_by_project

    def check_existing_path_conflicts(self, files: List[dict]) -> List[dict]:
        """Check that new file paths don't conflict with existing ones."""
        new_files = [f for f in files if ("id" not in f) and (f["storage_project"] is not None)]
        new_files_by_project = self.group_files_by_storage_project(new_files)
        for storage_project, new_project_files in new_files_by_project.items():
            new_file_paths = [f["file_path"] for f in new_project_files]
            conflicts = (
                storage_project.files.filter(
                    # prefilter results before doing a more expensive exact match with Concat
                    directory_path__in=set(p.rsplit("/", 1)[0] + "/" for p in new_file_paths),
                    file_name__in=set(p.rsplit("/", 1)[1] for p in new_file_paths),
                )
                .annotate(file_path=Concat("directory_path", "file_name"))
                .filter(
                    file_path__in=new_file_paths,
                )
                .values("file_path", "id")
            )
            if conflicts:
                conflicts_by_path = {c["file_path"]: c["id"] for c in conflicts}
                for f in new_project_files:
                    if f["file_path"] in conflicts_by_path:
                        f["errors"]["file_path"] = _(
                            "A file with the same path already exists, id='{fid}'."
                        ).format(fid=conflicts_by_path[f["file_path"]])
        return files

    def check_duplicate_paths(self, files: List[dict]) -> List[dict]:
        """Check that there are no conflicting file changes."""
        ok_files = [f for f in files if f["storage_project"] is not None]
        files_by_project = self.group_files_by_storage_project(ok_files)
        for project_files in files_by_project.values():
            values = set()
            for f in project_files:
                if "file_path" not in f:
                    continue
                value = f["file_path"]
                if value in values:
                    f["errors"]["file_path"] = _("Value conflicts with another file in request")
                else:
                    values.add(value)
        return files

    def flush_file_errors(self, files: List[dict]) -> List[dict]:
        """Return only files that have no errors."""
        ok_values = []
        for f in files:
            if errors := f.pop("errors"):
                # Add invalid files to self.failed
                self.fail(object=f["original_data"], errors=errors)
            else:
                ok_values.append(f)
        return ok_values

    def to_internal_value(self, data) -> List[dict]:
        files = super().to_internal_value(data)

        # Identifier checks
        files = self.check_id_field_allowed(files)
        files = self.check_ids_exist(files)
        # TODO: Populate id for values with only external id
        files = self.check_duplicate_ids(files)

        # Checks for required and forbidden values
        files = self.check_files_allowed_actions(files)
        files = self.check_new_files_required_fields(files)

        # Assign StorageProject and related values
        files = self.assign_existing_project_data(files)
        files = self.assign_storage_project_to_files(files)

        # Path checks
        files = self.check_existing_path_conflicts(files)
        files = self.check_duplicate_paths(files)

        return self.flush_file_errors(files)

    def update_file_instance(self, instance, file_data) -> Optional[File]:
        """Update instance attributes of a File instance.

        Returns the updated file, or None if there were errors."""
        # store original data for error messages
        errors = {}
        for field, value in file_data.items():
            if field in FileSerializer.create_only_fields:
                existing_value = getattr(instance, field, None)
                if field == "file_storage":
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
        instance.modified = timezone.now()
        return instance

    def get_file_instances(self, validated_data) -> List[File]:
        """Return not yet saved instances from validated data."""
        system_creator = get_technical_metax_user()

        existing_files_by_id = File.available_objects.prefetch_related("storage_project").in_bulk(
            [f["id"] for f in validated_data if "id" in f]
        )

        files = []
        for f in validated_data:
            if "id" not in f:  # new file
                # Note: To determine if a File instance is not yet in the DB,
                # use instance._state.adding. For a UUID-style id, the id is
                # set on instantiation instead of on save, so checking
                # `id is None` won't work.
                original_data = f.pop("original_data")
                f.pop("project_identifier", None)  # included in StorageProject
                f.pop("file_storage", None)  # included in StorageProject
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
        return files

    def do_create_or_update(self, files: List[File]) -> List[dict]:
        """Perform bulk create and update actions for files."""
        fields_to_update = {
            field.name
            for field in File._meta.get_fields()
            if field.concrete and field.name not in {"id", *FileSerializer.create_only_fields}
        }

        being_created = {f.id for f in files if f._state.adding}
        files_to_create = [f for f in files if f.id in being_created]
        files_to_update = [f for f in files if f.id not in being_created]

        File.objects.bulk_create(files_to_create)
        File.objects.bulk_update(files_to_update, fields=fields_to_update)

        # Get new and updated values from db
        new_files_by_id = File.objects.prefetch_related("storage_project").in_bulk(
            [f.id for f in files]
        )
        new_files = []  # List files in original order
        for f in files:
            if new_file := new_files_by_id.get(f.id, None):
                new_files.append(new_file)
            else:
                # This should not happen unless bulk_create manages to fail silently
                self.fail(
                    object=f._original_data,
                    errors={api_settings.NON_FIELD_ERRORS_KEY: _("Unknown error.")},
                )

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
            for f in new_files
        ]

    def do_delete(self, files: List[File]) -> List[dict]:
        """Perform bulk delete on files."""
        file_ids = [f.id for f in files]
        File.objects.filter(id__in=file_ids).delete()
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
