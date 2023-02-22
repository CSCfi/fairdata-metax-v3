# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


from django.db.models import CharField, Count, F, Max, Min, Sum, Value
from django.db.models.functions import Concat, JSONObject
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, fields, serializers, viewsets
from rest_framework.response import Response

from apps.files.functions import SplitPart
from apps.files.helpers import remove_query_param, replace_query_param
from apps.files.models.file import File, StorageProject
from apps.files.serializers.directory_serializer import (
    DirectoryFileSerializer,
    DirectorySerializer,
    SubDirectorySerializer,
)
from apps.files.serializers.fields import CommaSeparatedListField, OptionalSlashDirectoryPathField


class DirectoryCommonQueryParams(serializers.Serializer):
    """Serializer for parsing directory query parameters."""

    allowed_file_fields = sorted(DirectoryFileSerializer().get_fields())
    allowed_file_orderings = [
        "file_name",
        "file_path",
        "byte_size",
        "created",
        "modified",
        "date_frozen",
        "file_modified",
        "date_deleted",
    ]
    allowed_file_orderings += [f"-{field}" for field in allowed_file_orderings]

    allowed_directory_fields = sorted(SubDirectorySerializer().get_fields())
    allowed_directory_orderings = allowed_directory_fields + [
        f"-{field}" for field in allowed_directory_fields
    ]

    path = OptionalSlashDirectoryPathField(default="/")
    include_parent = fields.BooleanField(default=True)

    # directory filters (only affect direct children of current directory)
    name = fields.CharField(default=None)
    directory_fields = CommaSeparatedListField(
        default=None,
        child=serializers.ChoiceField(choices=allowed_directory_fields),
    )
    directory_ordering = CommaSeparatedListField(
        default=list,
        child=serializers.ChoiceField(choices=allowed_directory_orderings),
    )
    file_fields = CommaSeparatedListField(
        default=None,
        child=serializers.ChoiceField(choices=allowed_file_fields),
    )
    file_ordering = CommaSeparatedListField(
        default=list,
        child=serializers.ChoiceField(choices=allowed_file_orderings),
    )

    # pagination
    pagination = fields.BooleanField(default=True)
    offset = fields.IntegerField(default=0)
    limit = fields.IntegerField(default=100)


class DirectoryQueryParams(DirectoryCommonQueryParams):
    """Add project, storage and dataset specific parameters for directory."""

    project_identifier = fields.CharField(write_only=True)
    file_storage = fields.CharField(write_only=True)

    # project_id is determined from project_identifier and file_storage
    storage_project_id = fields.CharField(read_only=True)

    # project-wide filters (affect nested files and returned file_count, byte_size)
    dataset = fields.UUIDField(default=None, help_text="Only list items in dataset.")
    exclude_dataset = fields.BooleanField(
        default=False, help_text="Only list items missing from dataset."
    )

    def validate(self, data):
        if data["exclude_dataset"] and not data["dataset"]:
            raise serializers.ValidationError(
                {
                    "exclude_dataset": "The dataset field is required when exclude_dataset is enabled."
                }
            )
        return data

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        project_identifier = value.pop("project_identifier")
        file_storage = value.pop("file_storage")

        try:
            value["storage_project_id"] = StorageProject.available_objects.get(
                project_identifier=project_identifier,
                file_storage=file_storage,
            ).id
        except StorageProject.DoesNotExist as e:
            raise exceptions.NotFound()
        return value


class DirectoryViewSet(viewsets.ViewSet):
    """API for browsing directories of a storage project.

    Directories are transient and do not have a model of their own.
    Instead, they are generated dynamically from files that match
    the requested path."""

    def get_params(self):
        """Parse view query parameters."""
        params_serializer = DirectoryQueryParams(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        return params_serializer.validated_data

    def get_project_files(self, params):
        """Get relevant project files."""
        filter_args = dict(
            storage_project_id=params["storage_project_id"],
        )
        exclude_args = dict()
        if dataset := params["dataset"]:
            if params["exclude_dataset"]:
                exclude_args["datasets"] = dataset
            else:
                filter_args["datasets"] = dataset
        filter_args = {
            key: value for (key, value) in filter_args.items() if value is not None
        }

        return File.available_objects.filter(**filter_args).exclude(**exclude_args)

    def annotate_file_property_fields(self, params, files):
        """Add File properties as annotations so they can be used with file_fields
        and file_ordering.

        When using the file_fields parameter, the File QuerySet uses .values()
        and returns dicts so File properties (e.g. file_path) are not available
        for the serializer unless explicitly added by annotation.

        Also, model properties cannot be used directly in queries (e.g. order_by)
        since they don't exist in the DB, but can be replicated with annotations.
        """
        used_file_fields = set(params["file_fields"] or [])
        used_ordering_fields = set(params["file_ordering"] or [])
        used_fields = used_file_fields | used_ordering_fields
        if "file_path" in used_fields or "-file_path" in used_fields:
            files = files.annotate(file_path=Concat("directory_path", "file_name"))
        if "checksum" in used_fields:
            files = files.annotate(
                checksum=JSONObject(
                    algorithm="checksum_algorithm",
                    checked="checksum_checked",
                    value="checksum_value",
                )
            )
        if "project_identifier" in used_fields:
            files = files.annotate(
                project_identifier=F("storage_project__project_identifier")
            )
        if "file_storage" in used_fields:
            files = files.annotate(file_storage=F("storage_project__file_storage"))
        return files

    def get_directory_files(self, params):
        """Get files that are directly contained in directory."""
        files = self.get_project_files(params).filter(
            directory_path=params["path"],
        )
        if name := params["name"]:
            files = files.filter(file_name__icontains=name)

        # retrive only requested fields
        files = self.annotate_file_property_fields(params, files)
        if file_fields := params["file_fields"]:
            files = files.values(*file_fields)

        return files.order_by(*params["file_ordering"], "file_name")

    def get_directories(self, params):
        """Get directory and subdirectory data for path.

        The query generates directory information from files as follows:
        * Get all files that start with path
        * Determine which subdirectory of path each file is in (=directory_name)
        * Aggregate files by directory_name

        Note: If path contains files directly (not in a subdirectory), it will also be included
        in the result with directory_name=="". Its file_count, byte_size, created and modified
        values include only the files it contains directly.
        """

        path = params["path"]
        subdirectory_level = path.count("/") + 1
        dirs = (
            self.get_project_files(params)
            .filter(
                directory_path__startswith=path,
            )
            .values(
                directory_name=SplitPart(
                    "directory_path",
                    Value("/"),
                    subdirectory_level,
                    output_field=CharField(),
                )
            )
            .annotate(
                file_count=Count("*"),
                byte_size=Sum("byte_size"),
                created=Min("created"),
                modified=Max("modified"),
                directory_path=Concat(  # append directory name and slash to path
                    Value(path),
                    F("directory_name"),
                    Value("/"),
                    output_field=CharField(),
                ),
            )
            .order_by(*params["directory_ordering"], "directory_name")
        )
        return dirs

    def paginate(self, params, subdirectories, files):
        """Paginate direcories and files together."""
        limit = params["limit"]
        offset = params["offset"]

        # Evaluate all subdirectories into a list so they can be
        # counted and sliced in a single DB query.
        subdirectories_list = list(subdirectories)
        paginated_dirs = subdirectories_list[offset : offset + limit]
        dir_count = len(subdirectories_list)

        paginated_files = []
        file_offset = max(0, offset - dir_count)
        file_limit = max(0, limit - len(paginated_dirs))
        paginated_files = files[file_offset : file_offset + file_limit]
        file_count = files.count()

        count = file_count + dir_count
        has_more = count > offset + limit
        last_idx = offset + len(paginated_dirs) + len(paginated_files)
        return {
            "count": file_count + dir_count,
            "directories": paginated_dirs,
            "files": paginated_files,
            "last_idx": last_idx,
            "has_more": has_more,
        }

    def get_pagination_data(self, request, params, paginated):
        """Get pagination count and links for the response."""
        data = {"count": paginated["count"], "next": None, "previous": None}

        previous_idx = None
        uri = request.build_absolute_uri()
        if paginated["has_more"] and paginated["last_idx"]:
            data["next"] = replace_query_param(uri, "offset", paginated["last_idx"])

        if params["offset"] > 0:
            previous_idx = max(params["offset"] - params["limit"], 0)
            if previous_idx > 0:
                data["previous"] = replace_query_param(uri, "offset", previous_idx)
            else:
                data["previous"] = remove_query_param(uri, "offset")
        return data

    def get_matching_subdirectories(self, params, directories):
        """Get subdirectories that match the filters."""
        subdirs = directories.exclude(directory_name="")  # exclude current dir
        if name := params.get("name"):
            subdirs = subdirs.filter(directory_name__icontains=name)
        return subdirs

    def get_parent_data(self, params, directories):
        """Aggregate totals for parent directory."""
        file_count = sum(d.get("file_count", 0) for d in directories)
        byte_size = sum(d.get("byte_size", 0) for d in directories)
        created = min((d.get("created") for d in directories), default=None)
        modified = max((d.get("modified") for d in directories), default=None)
        return {
            "parent_directory": {
                "directory_name": params["path"].split("/")[-2],
                "directory_path": params["path"],
                "file_count": file_count,
                "byte_size": byte_size,
                "created": created,
                "modified": modified,
            }
        }

    def get_storage_project(self, params):
        """Return storage project common for all subdirectories and files."""
        return StorageProject.objects.get(id=params.get("storage_project_id"))

    @swagger_auto_schema(
        query_serializer=DirectoryQueryParams, responses={200: DirectorySerializer}
    )
    def list(self, request, *args, **kwargs):
        """Directory content view."""

        params = self.get_params()
        directories = self.get_directories(params)
        parent_data = {}
        if params.get("include_parent"):
            parent_data = self.get_parent_data(params, directories)
        matching_subdirs = self.get_matching_subdirectories(params, directories)
        files = self.get_directory_files(params)

        pagination_data = {}
        if params.get("pagination"):
            paginated = self.paginate(params, matching_subdirs, files)
            matching_subdirs = paginated["directories"]
            files = paginated["files"]
            pagination_data = self.get_pagination_data(request, params, paginated)

        instance = {
            **parent_data,
            "directories": matching_subdirs,
            "files": files,
        }

        # all directories and files have same project, pass it through context
        storage_project = self.get_storage_project(params)
        serialized_data = DirectorySerializer(
            instance,
            context={
                "request": self.request,
                "directory_fields": params.get("directory_fields"),
                "file_fields": params.get("file_fields"),
                "storage_project": storage_project,
            },
        ).data
        results = serialized_data
        if params.get("pagination"):
            results = {"results": serialized_data}

        # empty results may be due to pagination, remove parent dir if it does not actually exist
        if (
            "parent_directory" in results
            and not serialized_data["directories"]
            and not serialized_data["files"]
            and not directories.exists()
        ):
            del results["parent_directory"]

        return Response({**pagination_data, **results})
