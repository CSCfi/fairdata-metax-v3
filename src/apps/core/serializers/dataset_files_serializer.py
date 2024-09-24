# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from typing import Dict

from cachalot.api import cachalot_disabled
from django.db.models import Model, Q, TextChoices
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.common.serializers.fields import ListValidChoicesField
from apps.common.serializers.validators import AnyOf
from apps.core.models import FileSet
from apps.core.models.concepts import FileType, UseCategory
from apps.core.models.file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata
from apps.core.serializers.file_metadata_serializer import (
    DirectoryMetadataSerializer,
    FileMetadataSerializer,
)
from apps.files.models import FileStorage
from apps.files.serializers.fields import DirectoryPathField, StorageServiceField


class Action(TextChoices):
    ADD = "add", _("Add file or files contained by directory to dataset")
    REMOVE = "remove", _("Remove file or files contained by directory from dataset")
    UPDATE = "update", _("Update dataset-specific metadata for file or directory")


class ActionSerializerBase(StrictSerializer):
    action = ListValidChoicesField(choices=Action.choices, default=Action.ADD)


class FileActionSerializer(ActionSerializerBase):
    """Serializer for adding/removing a file and optionally updating dataset-specific metadata."""

    id = serializers.UUIDField(required=False, allow_null=True)
    storage_identifier = serializers.CharField(required=False, allow_null=True)
    pathname = serializers.CharField(required=False, allow_null=True)
    dataset_metadata = FileMetadataSerializer(required=False, allow_null=True)

    class Meta:
        validators = [AnyOf(["id", "storage_identifier", "pathname"])]


class DirectoryActionSerializer(ActionSerializerBase):
    """Serializer for adding/removing a directory and updating dataset-specific metadata."""

    pathname = DirectoryPathField()
    dataset_metadata = DirectoryMetadataSerializer(required=False, allow_null=True)
    only_unpublished = serializers.BooleanField(
        default=False, help_text="Only add/remove files not in any published dataset."
    )


class FileSetSerializer(StrictSerializer):
    """Serializer for FileSet and its file relations.

    Returns summary of files with file storage information and file statistics.

    Allows updating data file relations when provided with data in format
    ```
    {
        "storage_service": ...
        "csc_project": ...
        "directory_actions": [{"action": "add", "pathname": ..., "dataset_metadata": ...}]
        "file_actions": [{"action": "update", "id": ..., "dataset_metadata": ...}]
    }
    ```
    where action is either
    * "add" (default): Add file or all files in directory, update dataset_metadata if present
    * "update": Only update dataset_metadata without adding or removing files
    * "remove": Remove file or all files in directory and subdirecories

    Set dataset_metadata to null to remove existing metadata.

    The order of actions within the "directory_actions" and "file_actions" arrays is
    meaningful. First, directory actions are executed in sequence. Then file actions
    are executed in sequence. Finally, dataset-specific metadata for files and
    directories that no longer belonging to the dataset will be removed.

    Usage:
    * To create or update FileSet, call `.create(validated_data, dataset)`.
      Dataset argument can be omitted if it's in serializer context.
    * To update existing FileSet, call `.update(instance, validated_data)`.
    """

    directory_actions = DirectoryActionSerializer(many=True, required=False, write_only=True)
    file_actions = FileActionSerializer(many=True, required=False, write_only=True)

    storage_service = StorageServiceField(source="storage.storage_service")
    csc_project = serializers.CharField(source="storage.csc_project", required=False)

    added_files_count = serializers.IntegerField(read_only=True)
    removed_files_count = serializers.IntegerField(read_only=True)
    total_files_count = serializers.IntegerField(read_only=True)
    total_files_size = serializers.IntegerField(read_only=True)
    file_types = serializers.SerializerMethodField(read_only=True)

    def get_file_types(self, instance):
        if any(instance.file_types):
            file_types = {"en": set(), "fi": set()}
            for type in instance.file_types:
                if not type:
                    continue
                file_types["en"].add(type.get("en"))
                file_types["fi"].add(type.get("fi"))

            return {"en": sorted(file_types["en"]), "fi": sorted(file_types["fi"])}

    def assign_reference_data(self, actions: list, key: str, model: Model):
        """Replace reference data in actions' dataset_metadata with reference data instances."""
        if not actions:
            return

        # Get all used reference data urls
        urls = set()
        for action in actions:
            if metadata := action.get("dataset_metadata"):
                if item := metadata.get(key):
                    urls.add(item["url"])

        # Get dict of model instances by url
        refdata_by_url = model.objects.distinct("url").in_bulk(urls, field_name="url")
        if invalid_types := urls - set(refdata_by_url):
            raise serializers.ValidationError(
                {key: _("Invalid values: {values}").format(key=key, values=list(invalid_types))}
            )
        # Assign model instances to dataset_metadata
        for action in actions:
            if metadata := action.get("dataset_metadata"):
                if item := metadata.get(key):
                    metadata[key] = refdata_by_url.get(item["url"])

    def assign_file_ids(self, storage: FileStorage, file_actions: list):
        """Assign file identifiers to actions based on unique fields.

        Assigns the following uniquely identifying values to file actions
        and checks them for conflicts:
        - id
        - storage_identifier (unique for FileStorage)
        - pathname (unique for FileStorage)
        Also sets `_found=True` if file was found.
        """

        if not file_actions:
            return

        def check_value_conflicts(action: dict, file: dict, field: str):
            """Raise error if action field has different value than file in DB."""
            if existing_value := action.get(field):
                if existing_value != file[field]:
                    raise serializers.ValidationError(
                        {
                            field: _(
                                "Value conflict. Expected '{file_value}', got '{existing_value}'."
                            ).format(
                                field=field,
                                file_value=file[field],
                                existing_value=existing_value,
                            )
                        }
                    )

        def assign_values(actions_dict: dict, lookup_field: str, file_values: dict):
            """Assign file values from DB to action."""
            for file in file_values:
                for action in actions_dict[file[lookup_field]]:
                    for field in ("id", "storage_identifier", "pathname"):
                        check_value_conflicts(action, file, field)
                    action.update(file)
                    action["_found"] = True

        # Group files by the unique fields (note that a file is allowed to have multiple actions)
        storage_files = storage.files.annotate(pathname=Concat("directory_path", "filename"))
        by_id = {}
        by_storage_identifier = {}
        by_pathname = {}
        for f in file_actions:
            if "id" in f:
                by_id.setdefault(f["id"], []).append(f)
            if "storage_identifier" in f:
                by_storage_identifier.setdefault(f["storage_identifier"], []).append(f)
            if "pathname" in f:
                by_pathname.setdefault(f["pathname"], []).append(f)

        files_from_id = storage_files.filter(id__in=by_id).values(
            "id", "storage_identifier", "pathname"
        )
        assign_values(by_id, "id", files_from_id)

        files_from_storage_identifier = storage_files.filter(
            storage_identifier__in=by_storage_identifier
        ).values("id", "storage_identifier", "pathname")
        assign_values(by_storage_identifier, "storage_identifier", files_from_storage_identifier)

        files_from_pathname = (
            storage_files.filter(
                # prefilter results before doing a more expensive exact match with Concat
                directory_path__in=set(p.rsplit("/", 1)[0] + "/" for p in by_pathname),
                filename__in=set(p.rsplit("/", 1)[1] for p in by_pathname),
            )
            .filter(pathname__in=by_pathname)
            .values("id", "storage_identifier", "pathname")
        )
        assign_values(by_pathname, "pathname", files_from_pathname)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)

        # Replace storage dict with a FileStorage instance.
        storage_params = value.pop("storage", {})
        FileStorage.validate_object(storage_params)
        try:
            storage = FileStorage.available_objects.get(
                csc_project=storage_params.get("csc_project"),
                storage_service=storage_params.get("storage_service"),
            )
            value["storage"] = storage
        except FileStorage.DoesNotExist:
            storage: FileStorage = None

            # Special case to allow associating dataset with a project that has no files yet.
            # Directory and file actions will fail in any case without files so don't
            # attempt to create a FileStorage if there are any actions.
            if not value.get("directory_actions") and not value.get("file_actions"):
                storage = FileStorage.get_proxy_instance(**storage_params)
                user = self.context["request"].user
                try:
                    # User needs access to csc_project to create a matching FileStorage
                    storage.check_user_can_access(user)
                    storage.save()
                except serializers.ValidationError:
                    storage = None

            if not storage:
                raise serializers.ValidationError(
                    {
                        "storage": _("File storage not found with parameters {}.").format(
                            storage_params
                        )
                    }
                )
            value["storage"] = storage

        self.assign_file_ids(storage=value["storage"], file_actions=value.get("file_actions"))

        # Convert file_type dicts to FileType instances
        self.assign_reference_data(value.get("file_actions"), key="file_type", model=FileType)

        # Convert use_category dicts to UseCategory instances
        all_actions = [*value.get("file_actions", []), *value.get("directory_actions", [])]
        self.assign_reference_data(all_actions, key="use_category", model=UseCategory)

        return value

    def to_representation(self, instance):
        """Remove file additions and removals from response when files are not being changed."""
        rep = super().to_representation(instance)
        instance.storage.remove_unsupported_extra_fields(rep)

        if rep["added_files_count"] is None:
            del rep["added_files_count"]
        if rep["removed_files_count"] is None:
            del rep["removed_files_count"]

        if rep["file_types"] is None:
            del rep["file_types"]
        return rep

    def get_file_exist_errors(self, attrs) -> Dict:
        """Validate that all requested files exist, return error if not."""
        if file_actions := attrs.get("file_actions"):
            if missing_file := next((f for f in file_actions if not f.pop("_found", False)), None):
                missing_file.pop("action")
                raise serializers.ValidationError(
                    {
                        "file_actions": _("File not found in FileStorage: {}").format(
                            dict(missing_file)
                        )
                    }
                )
        return {}

    def get_directory_exist_errors(self, attrs) -> Dict:
        """Validate that all requested directories exist, return error if not."""
        if directory_actions := attrs.get("directory_actions"):
            project_directory_paths = attrs["storage"].get_directory_paths()
            action_pathnames = set(d["pathname"] for d in directory_actions)
            dirs_not_found = action_pathnames - project_directory_paths
            if dirs_not_found:
                return {
                    "pathname": _("Directory not found: {paths}").format(
                        paths=sorted(dirs_not_found)
                    )
                }
        return {}

    def get_items_exist_errors(self, attrs):
        """Return dict containing any errors from nonexisting directories or files."""
        return {
            **self.get_file_exist_errors(attrs),
            **self.get_directory_exist_errors(attrs),
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if errors := self.get_items_exist_errors(attrs):
            raise serializers.ValidationError(errors)
        return attrs

    def validate_correct_storage(self, file_set: FileSet, attrs: dict):
        """Check that new files don't belong to different FileStorage than FileSet."""
        if file_set:
            errors = {}
            if file_set.storage.csc_project != attrs["storage"].csc_project:
                errors["csc_project"] = _("Wrong csc_project for fileset.")
            if file_set.storage.storage_service != attrs["storage"].storage_service:
                errors["storage_service"] = _("Wrong storage_service for fileset.")
            if errors:
                raise serializers.ValidationError(errors)

    def get_directory_filters(self, directory_actions) -> Dict:
        """Get Q objects for directory additions and removals.

        Filters are joined as if directories were added or removed in sequence:
        * Addition cancels an earlier removal
        * Removal cancels an earlier addition
        """
        adds = Q()
        removes = Q()
        for action in directory_actions:
            filtr = Q(directory_path__startswith=action["pathname"])
            if action["only_unpublished"]:
                filtr &= Q(published__isnull=True)
            if action["action"] == Action.ADD:
                adds = adds | filtr
                if removes:
                    removes = removes & ~filtr
            elif action["action"] == Action.REMOVE:
                removes = removes | filtr
                if adds:
                    adds = adds & ~filtr

        filters = {}
        if adds:
            filters["add"] = adds
        if removes:
            filters["remove"] = removes
        return filters

    def get_file_filters(self, file_actions) -> Dict:
        """Get Q objects for file additions and removals."""
        last_file_actions = {}  # determine last addition/removal action for each file
        for action in file_actions:
            if action["action"] in (Action.ADD, Action.REMOVE):
                last_file_actions[action["id"]] = action

        added_files = set(
            action["id"] for action in last_file_actions.values() if action["action"] == Action.ADD
        )
        removed_files = set(
            action["id"]
            for action in last_file_actions.values()
            if action["action"] == Action.REMOVE
        )

        filters = {}
        if added_files:
            filters["add"] = Q(id__in=added_files)
        if removed_files:
            filters["remove"] = Q(id__in=removed_files)
        return filters

    def get_filters(self, directory_actions, file_actions):
        """Get Q objects combining directory and file additions and removals."""
        combined_adds = Q()
        combined_removes = Q()
        if directory_actions:
            directory_filters = self.get_directory_filters(directory_actions)
            if add := directory_filters.get("add"):
                combined_adds = combined_adds | add
            if remove := directory_filters.get("remove"):
                combined_removes = combined_removes | remove

        if file_actions:
            file_filters = self.get_file_filters(file_actions)
            if add := file_filters.get("add"):
                combined_adds = combined_adds | add
                if combined_removes:
                    combined_removes = combined_removes & ~add
            if remove := file_filters.get("remove"):
                combined_removes = combined_removes | remove
                if combined_adds:
                    combined_adds = combined_adds & ~remove

        # avoid returning empty Q objects that would match all
        return {
            "add": combined_adds or None,
            "remove": combined_removes or None,
        }

    def get_metadata_updating_actions(self, actions):
        """Return actions that may update dataset_metadata."""
        return [
            action
            for action in actions
            if "dataset_metadata" in action and action["action"] in (Action.ADD, Action.UPDATE)
        ]

    def update_file_metadata(self, file_actions, file_set):
        """Update dataset_metadata for files."""
        if not file_actions:
            return

        # get last metadata update for file by id
        metadata_actions = self.get_metadata_updating_actions(file_actions)
        file_metadata = {}
        for action in metadata_actions:
            file_metadata[action["id"]] = action["dataset_metadata"]

        # get existing metadata instances
        file_metadata_instances = FileSetFileMetadata.objects.filter(
            file_set=file_set, file_id__in=set(file_metadata)
        )
        file_metadata_instances_by_key = {fm.file_id: fm for fm in file_metadata_instances}

        # update instances or create new ones
        new_file_metadata = []
        removed_file_metadata_ids = []
        for id, metadata in file_metadata.items():
            instance = file_metadata_instances_by_key.get(id)
            if metadata is None:
                if instance:
                    removed_file_metadata_ids.append(instance.id)  # remove metadata entry
            elif instance:
                for attr, value in metadata.items():  # title, description, use_category
                    setattr(instance, attr, value)  # assign new values

            else:
                new_file_metadata.append(
                    FileSetFileMetadata(
                        file_set=file_set,
                        file_id=id,
                        **metadata,
                    )
                )

        FileSetFileMetadata.objects.bulk_update(
            file_metadata_instances,
            fields=["title", "description", "file_type", "use_category"],
        )
        FileSetFileMetadata.objects.bulk_create(new_file_metadata)
        FileSetFileMetadata.objects.filter(id__in=removed_file_metadata_ids).delete()

    def update_directory_metadata(self, directory_actions, file_set, storage):
        """Update dataset_metadata for directories."""
        if not directory_actions:
            return

        # get last metadata update for directory by pathname
        metadata_actions = self.get_metadata_updating_actions(directory_actions)
        directory_metadata = {}
        for action in metadata_actions:
            directory_metadata[action["pathname"]] = action["dataset_metadata"]

        # get existing metadata instances
        directory_metadata_instances = FileSetDirectoryMetadata.objects.filter(
            file_set=file_set, pathname__in=set(directory_metadata)
        )
        directory_metadata_instances_by_key = {
            dm.pathname: dm for dm in directory_metadata_instances
        }

        # update instances or create new ones
        new_directory_metadata = []
        removed_directory_metadata_ids = []
        for path, metadata in directory_metadata.items():
            instance = directory_metadata_instances_by_key.get(path)
            if metadata is None:
                if instance:
                    removed_directory_metadata_ids.append(instance.id)  # remove metadata entry
            elif instance:
                for attr, value in metadata.items():
                    setattr(instance, attr, value)  # assign new values
            else:
                new_directory_metadata.append(
                    FileSetDirectoryMetadata(
                        file_set=file_set,
                        storage=storage,
                        pathname=path,
                        **metadata,
                    )
                )
        FileSetDirectoryMetadata.objects.bulk_update(
            directory_metadata_instances,
            fields=["title", "description", "use_category"],
        )
        FileSetDirectoryMetadata.objects.bulk_create(new_directory_metadata)
        FileSetDirectoryMetadata.objects.filter(id__in=removed_directory_metadata_ids).delete()

    def get_or_create_instance_for_dataset(self, validated_data, dataset) -> FileSet:
        data = validated_data or self.validated_data
        if (
            conflicting_file_set := FileSet.objects.filter(dataset=dataset)
            .exclude(storage=data["storage"])
            .first()
        ):
            raise serializers.ValidationError(
                {
                    "storage_service": _(
                        "Dataset already has a file set with parameters {}. Cannot add another."
                    ).format(conflicting_file_set.storage.params_dict)
                }
            )

        storage: FileStorage = data["storage"]
        user = self.context["request"].user
        try:
            return FileSet.available_objects.get(
                dataset=dataset,
                storage=storage,
            )
        except FileSet.DoesNotExist:
            # Creating new fileset only allowed if user has access to the csc_project
            storage.check_user_can_access(user)
            return FileSet.available_objects.create(
                dataset=dataset,
                storage=storage,
            )

    def create(self, validated_data):
        """Create or update FileSet and its file relations."""
        dataset = validated_data.get("dataset")
        if dataset is None:
            raise ValueError("Expected dataset instance in validated_data.")

        instance = self.get_or_create_instance_for_dataset(validated_data, dataset=dataset)
        return self.update(instance, validated_data)

    def check_file_changes_allowed(self, instance: FileSet):
        try:
            user = self.context["request"].user
            instance.storage.check_user_can_access(user)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                {"action": "Project membership is required for adding or removing files."}
            )

    def check_allow_removing_files(self, instance: FileSet):
        self.check_file_changes_allowed(instance)
        if not instance.dataset.allow_removing_files:
            raise serializers.ValidationError(
                {"action": _("Removing files from a published dataset is not allowed.")}
            )

    def check_allow_adding_files(self, instance: FileSet):
        self.check_file_changes_allowed(instance)
        if not instance.dataset.allow_adding_files:
            raise serializers.ValidationError(
                {"action": _("Adding files to a published noncumulative dataset is not allowed.")}
            )

    def update(self, instance: FileSet, validated_data):
        """Update file relations and metadata of FileSet."""
        file_set = instance

        storage: FileStorage = validated_data["storage"]
        directory_actions: list = validated_data.get("directory_actions", [])
        file_actions: list = validated_data.get("file_actions", [])

        self.validate_correct_storage(file_set, validated_data)

        filters = self.get_filters(directory_actions, file_actions)
        file_set.skip_files_m2m_changed = (
            True  # avoid running metadata cleanup step multiple times
        )
        file_set.removed_files_count = 0
        file_set.added_files_count = 0

        with cachalot_disabled():
            # remove files
            if filters["remove"]:
                files_to_remove = (
                    file_set.files.filter(filters["remove"])
                    .order_by()
                    .values_list("id", flat=True)
                )
                file_set.removed_files_count = len(files_to_remove)
                if file_set.removed_files_count > 0:
                    self.check_allow_removing_files(instance)

                file_set.files.remove(*files_to_remove)

            # add files
            if filters["add"]:
                files_to_add = (
                    storage.files.exclude(file_sets=file_set.id)
                    .filter(filters["add"])
                    .order_by()
                    .values_list("id", flat=True)
                )
                file_set.added_files_count = len(files_to_add)
                if file_set.added_files_count > 0:
                    self.check_allow_adding_files(instance)

                file_set.files.add(*files_to_add)
                file_set.update_published()

        # file counts and dataset storage project may have changed, clear cached values
        file_set.clear_cached_file_properties()

        # update dataset-specific metadata
        self.update_file_metadata(file_actions, file_set)
        self.update_directory_metadata(directory_actions, file_set, storage)

        # remove any metadata that points to items not in dataset
        file_set.remove_unused_file_metadata()

        return instance
