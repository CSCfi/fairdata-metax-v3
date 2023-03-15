# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from typing import Dict

from django.db.models import Model, Q, TextChoices
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.models import Dataset
from apps.core.models.concepts import FileType, UseCategory
from apps.core.models.file_metadata import DatasetDirectoryMetadata, DatasetFileMetadata
from apps.core.serializers.file_metadata_serializer import (
    DirectoryMetadataSerializer,
    FileMetadataSerializer,
)
from apps.files.models import FileStorage, StorageProject
from apps.files.serializers.fields import DirectoryPathField, ListValidChoicesField


class Action(TextChoices):
    ADD = "add", _("Add file or files contained by directory to dataset")
    REMOVE = "remove", _("Remove file or files contained by directory from dataset")
    UPDATE = "update", _("Update dataset-specific metadata for file or directory")


class ActionSerializerBase(serializers.Serializer):
    action = ListValidChoicesField(choices=Action.choices, default=Action.ADD)


class FileActionSerializer(ActionSerializerBase):
    """Serializer for adding/removing a file and optionally updating dataset-specific metadata."""

    id = serializers.UUIDField()
    dataset_metadata = FileMetadataSerializer(required=False, allow_null=True)


class DirectoryActionSerializer(ActionSerializerBase):
    """Serializer for adding/removing a directory and updating dataset-specific metadata."""

    directory_path = DirectoryPathField()
    dataset_metadata = DirectoryMetadataSerializer(required=False, allow_null=True)


class DatasetFilesSerializer(serializers.Serializer):
    """Serializer for dataset file relations.

    Returns summary of dataset files with project information and file statistics.

    Allows updating data file relations when provided with data in format
    ```
    {
        "project_identifier": ...
        "file_storage": ...
        "directory_actions": [{"action": "add", "directory_path": ..., "dataset_metadata": ...}]
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

    Call `update(instance, validated_data)` to apply changes. The instance argument
    should be a Dataset.files manager."""

    directory_actions = DirectoryActionSerializer(many=True, required=False, write_only=True)
    file_actions = FileActionSerializer(many=True, required=False, write_only=True)

    # Instance provided to the serializer is expected to be a Dataset.files manager.
    # The instance in source then refers to dataset.files.instance, which is the dataset itself.
    project_identifier = serializers.CharField(source="instance.project_identifier")
    file_storage = serializers.PrimaryKeyRelatedField(
        queryset=FileStorage.objects.all(), source="instance.file_storage"
    )

    added_files_count = serializers.IntegerField(
        read_only=True, source="instance.added_files_count"
    )
    removed_files_count = serializers.IntegerField(
        read_only=True, source="instance.removed_files_count"
    )
    total_files_count = serializers.IntegerField(
        read_only=True, source="instance.total_files_count"
    )
    total_files_byte_size = serializers.IntegerField(
        read_only=True, source="instance.total_files_byte_size"
    )

    def assign_reference_data(self, actions: list, key: str, model: Model):
        """Replace reference data in actions' dataset_metadata with reference data instances."""
        if not actions:
            return

        # Get all used reference data urls
        urls = set()
        for action in actions:
            if metadata := action.get("dataset_metadata"):
                if key in metadata:
                    urls.add(metadata[key]["url"])

        # Get dict of model instances by url
        refdata_by_url = model.objects.distinct("url").in_bulk(urls, field_name="url")
        if invalid_types := urls - set(refdata_by_url):
            raise serializers.ValidationError(
                {
                    key: _("Invalid {key} values: {values}").format(
                        key=key, values=list(invalid_types)
                    )
                }
            )
        # Assign model instances to dataset_metadata
        for action in actions:
            if metadata := action.get("dataset_metadata"):
                if key in metadata:
                    metadata[key] = refdata_by_url.get(metadata[key]["url"])

    def to_internal_value(self, data):
        value = super().to_internal_value(data)

        # Move values from under instance to data root,
        # e.g. value["instance"]["project_identifier"] becomes value["project_identifier"]
        values_from_dataset = value.pop("instance")
        value = {**value, **values_from_dataset}

        # Get storage project, assign to value
        try:
            proj = StorageProject.available_objects.get(
                project_identifier=value["project_identifier"],
                file_storage_id=value["file_storage"],
            )
            value["storage_project"] = proj
        except StorageProject.DoesNotExist:
            raise serializers.ValidationError(
                {"storage_project": _("Invalid file_storage or project_identifier")}
            )

        # Convert file_type dicts to FileType instances
        self.assign_reference_data(value.get("file_actions"), key="file_type", model=FileType)

        # Convert use_category dicts to UseCategory instances
        all_actions = [*value.get("file_actions", []), *value.get("directory_actions", [])]
        self.assign_reference_data(all_actions, key="use_category", model=UseCategory)

        return value

    def to_representation(self, instance):
        """Remove file additions and removals from response when files are not being changed."""
        rep = super().to_representation(instance)

        if rep["added_files_count"] is None:
            del rep["added_files_count"]
        if rep["removed_files_count"] is None:
            del rep["removed_files_count"]
        return rep

    def get_file_exist_errors(self, attrs) -> Dict:
        """Validate that all requested files exist, return error if not."""
        if file_actions := attrs.get("file_actions"):
            file_ids = set(f["id"] for f in file_actions)
            found_files = set(
                attrs["storage_project"].files.filter(id__in=file_ids).values_list("id", flat=True)
            )
            files_not_found = file_ids - found_files
            if files_not_found:
                return {
                    "file.id": _("Files not found in project: {ids}").format(
                        ids=sorted([str(f) for f in files_not_found])
                    )
                }
        return {}

    def get_directory_exist_errors(self, attrs) -> Dict:
        """Validate that all requested directories exist, return error if not."""
        if directory_actions := attrs.get("directory_actions"):
            project_directory_paths = attrs["storage_project"].get_directory_paths()
            action_directory_paths = set(d["directory_path"] for d in directory_actions)
            dirs_not_found = action_directory_paths - project_directory_paths
            if dirs_not_found:
                return {
                    "directory_path": _("Directory not found: {paths}").format(
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
        errors = self.get_items_exist_errors(attrs)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def validate_dataset_storage_project(self, dataset, attrs):
        """Check that new files don't belong to different StorageProject than dataset."""
        if dataset:
            if dataset_storage_project := dataset.storage_project:
                errors = {}
                if dataset_storage_project.project_identifier != attrs["project_identifier"]:
                    errors["project_identifier"] = _("Wrong project_identifier for dataset.")
                if dataset_storage_project.file_storage != attrs["file_storage"]:
                    errors["file_storage"] = _("Wrong file_storage for dataset.")
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
            filtr = Q(directory_path__startswith=action["directory_path"])
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
            if remove := file_filters.get("remove"):
                combined_removes = combined_removes | remove

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

    def update_file_metadata(self, file_actions, dataset):
        """Update dataset_metadata for files."""
        if not file_actions:
            return

        # get last metadata update for file by id
        metadata_actions = self.get_metadata_updating_actions(file_actions)
        file_metadata = {}
        for action in metadata_actions:
            file_metadata[action["id"]] = action["dataset_metadata"]

        # get existing metadata instances
        file_metadata_instances = DatasetFileMetadata.objects.filter(
            dataset=dataset, file_id__in=set(file_metadata)
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
                    DatasetFileMetadata(
                        dataset=dataset,
                        file_id=id,
                        **metadata,
                    )
                )

        DatasetFileMetadata.objects.bulk_update(
            file_metadata_instances,
            fields=["title", "description", "file_type", "use_category"],
        )
        DatasetFileMetadata.objects.bulk_create(new_file_metadata)
        DatasetFileMetadata.objects.filter(id__in=removed_file_metadata_ids).delete()

    def update_directory_metadata(self, directory_actions, dataset, storage_project):
        """Update dataset_metadata for directories."""
        if not directory_actions:
            return

        # get last metadata update for directory by directory_path
        metadata_actions = self.get_metadata_updating_actions(directory_actions)
        directory_metadata = {}
        for action in metadata_actions:
            directory_metadata[action["directory_path"]] = action["dataset_metadata"]

        # get existing metadata instances
        directory_metadata_instances = DatasetDirectoryMetadata.objects.filter(
            dataset=dataset, directory_path__in=set(directory_metadata)
        )
        directory_metadata_instances_by_key = {
            dm.directory_path: dm for dm in directory_metadata_instances
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
                    DatasetDirectoryMetadata(
                        dataset=dataset,
                        storage_project=storage_project,
                        directory_path=path,
                        **metadata,
                    )
                )
        DatasetDirectoryMetadata.objects.bulk_update(
            directory_metadata_instances,
            fields=["title", "description", "use_category"],
        )
        DatasetDirectoryMetadata.objects.bulk_create(new_directory_metadata)
        DatasetDirectoryMetadata.objects.filter(id__in=removed_directory_metadata_ids).delete()

    def update(self, instance: Dataset.files.related_manager_cls, validated_data):
        """Update file relations and metadata for dataset."""
        dataset: Dataset = instance.instance
        storage_project: StorageProject = validated_data["storage_project"]
        directory_actions: list = validated_data.get("directory_actions", [])
        file_actions: list = validated_data.get("file_actions", [])

        self.validate_dataset_storage_project(dataset, validated_data)

        filters = self.get_filters(directory_actions, file_actions)
        dataset.skip_files_m2m_changed = True  # avoid running metadata cleanup step multiple times
        dataset.removed_files_count = 0
        dataset.added_files_count = 0

        # remove files
        if filters["remove"]:
            files_to_remove = (
                dataset.files.filter(filters["remove"]).order_by().values_list("id", flat=True)
            )
            dataset.removed_files_count = len(files_to_remove)
            dataset.files.remove(*files_to_remove)

        # add files
        if filters["add"]:
            files_to_add = (
                storage_project.files.exclude(datasets=dataset.id)
                .filter(filters["add"])
                .order_by()
                .values_list("id", flat=True)
            )
            dataset.added_files_count = len(files_to_add)
            dataset.files.add(*files_to_add)

        # file counts and dataset storage project may have changed, clear cached values
        dataset.clear_cached_file_properties()

        # update dataset-specific metadata
        self.update_file_metadata(file_actions, dataset)
        self.update_directory_metadata(directory_actions, dataset, storage_project)

        # remove any metadata that points to items not in dataset
        dataset.remove_unused_file_metadata()

        return instance
