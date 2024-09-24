# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from django.db.models import CharField, Count, F, Max, Min, Sum, Value
from django.db.models.functions import Concat
from drf_yasg.utils import swagger_auto_schema
from rest_access_policy import AccessViewSetMixin
from rest_framework import fields, serializers, viewsets
from rest_framework.response import Response

from apps.common.helpers import cachalot_toggle, get_attr_or_item
from apps.common.views import QueryParamsMixin
from apps.common.serializers.fields import CommaSeparatedListField
from apps.files.functions import SplitPart
from apps.files.helpers import (
    get_directory_metadata_model,
    get_file_metadata_model,
    remove_query_param,
    replace_query_param,
)
from apps.files.models.file import File, FileStorage
from apps.files.permissions import DirectoriesAccessPolicy
from apps.files.serializers.directory_serializer import (
    DirectoryFileSerializer,
    DirectorySerializer,
    SubDirectorySerializer,
)
from apps.files.serializers.fields import (
    OptionalSlashDirectoryPathField,
    StorageServiceField,
)


class DirectoryCommonQueryParams(serializers.Serializer):
    """Serializer for parsing directory query parameters."""

    allowed_file_fields = sorted(DirectoryFileSerializer().get_fields())
    allowed_file_orderings = [
        "filename",
        "pathname",
        "size",
        "frozen",
        "modified",
        "deleted",
    ]
    allowed_file_orderings += [f"-{field}" for field in allowed_file_orderings]

    allowed_directory_fields = sorted(SubDirectorySerializer().get_fields())
    allowed_directory_orderings = allowed_directory_fields + [
        f"-{field}" for field in allowed_directory_fields
    ]

    path = OptionalSlashDirectoryPathField(default="/")
    include_parent = fields.BooleanField(default=True)
    published = fields.BooleanField(default=None, allow_null=True)
    count_published = fields.BooleanField(default=False)

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

    storage_service = StorageServiceField(write_only=True)
    csc_project = fields.CharField(write_only=True, default=None)

    # FileStorage is determined from project and storage_service
    storage_id = fields.CharField(read_only=True)

    # project-wide filters (affect nested files and returned file_count, size)
    dataset = fields.UUIDField(
        default=None, help_text="List items in dataset and associated dataset_metadata."
    )
    include_all = fields.BooleanField(
        default=False, help_text="When enabled and dataset is set, list also items not in dataset."
    )
    exclude_dataset = fields.BooleanField(
        default=False, help_text="When enabled, only list items missing from dataset."
    )

    def validate(self, data):
        if data["include_all"] and data["exclude_dataset"]:
            raise serializers.ValidationError(
                {
                    "exclude_dataset": "Fields include_all and exclude_dataset cannot be used together."
                }
            )
        if data["exclude_dataset"] and not data["dataset"]:
            raise serializers.ValidationError(
                {
                    "exclude_dataset": "The dataset field is required when exclude_dataset is enabled."
                }
            )
        return data

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        value["storage_id"] = FileStorage.objects.get_for_object(value).id
        return value


class DirectoryViewSet(QueryParamsMixin, AccessViewSetMixin, viewsets.ViewSet):
    """API for browsing directories of a storage project.

    Directories are transient and do not have a model of their own.
    Instead, they are generated dynamically from files that match
    the requested path."""

    access_policy = DirectoriesAccessPolicy

    # Query serializer info for query_params and swagger generation
    query_serializers = [
        {
            "class": DirectoryQueryParams,
        }
    ]

    def get_project_files(self, params):
        """Get relevant project files."""
        filter_args = dict(
            storage_id=params["storage_id"],
        )
        exclude_args = dict()
        if dataset := params["dataset"]:
            if params["exclude_dataset"]:
                exclude_args["file_sets__dataset"] = dataset
            elif not params["include_all"]:
                filter_args["file_sets__dataset"] = dataset
        filter_args = {key: value for (key, value) in filter_args.items() if value is not None}

        return File.available_objects.filter(**filter_args).exclude(**exclude_args)

    def annotate_file_property_fields(self, params, files):
        """Add File properties as annotations so they can be used with file_fields
        and file_ordering.

        When using the file_fields parameter, the File QuerySet uses .values()
        and returns dicts so File properties (e.g. pathname) are not available
        for the serializer unless explicitly added by annotation.

        Also, model properties cannot be used directly in queries (e.g. order_by)
        since they don't exist in the DB, but can be replicated with annotations.
        """
        used_file_fields = set(params["file_fields"] or [])
        used_ordering_fields = set(params["file_ordering"] or [])
        used_fields = used_file_fields | used_ordering_fields
        if "pathname" in used_fields or "-pathname" in used_fields:
            files = files.annotate(pathname=Concat("directory_path", "filename"))
        if "csc_project" in used_file_fields:
            files = files.annotate(csc_project=F("storage__csc_project"))
        return files

    def get_directory_files(self, params):
        """Get files that are directly contained in directory."""
        files = self.get_project_files(params).filter(
            directory_path=params["path"],
        )
        if name := params["name"]:
            files = files.filter(filename__icontains=name)
        if params["published"] is not None:
            files = files.filter(published__isnull=not params["published"])

        # retrieve only requested fields
        files = self.annotate_file_property_fields(params, files)
        if file_fields := params["file_fields"]:
            files = files.values(*file_fields, "id", storage_service=F("storage__storage_service"))

        return files.order_by(*params["file_ordering"], "filename")

    def get_directories(self, params):
        """Get directory and subdirectory data for path.

        The query generates directory information from files as follows:
        * Get all files that start with path
        * Determine which subdirectory of path each file is in (=name)
        * Aggregate files by directory name

        Note: If path contains files directly (not in a subdirectory), it will also be included
        in the result with directory name=="". Its file_count, size, created and modified
        values include only the files it contains directly.
        """

        path = params["path"]
        subdirectory_level = path.count("/") + 1
        file_filters = {}
        if params["published"] is not None:
            file_filters["published__isnull"] = not params["published"]

        dirs = (
            self.get_project_files(params)
            .filter(
                directory_path__startswith=path,
            )
            .values(
                name=SplitPart(
                    "directory_path",
                    Value("/"),
                    subdirectory_level,
                    output_field=CharField(),
                )
            )
            .annotate(
                file_count=Count("*"),
                published_file_count=Count("published"),
                size=Sum("size"),
                created=Min("modified"),
                modified=Max("modified"),
                pathname=Concat(  # append directory name and slash to path
                    Value(path),
                    F("name"),
                    Value("/"),
                    output_field=CharField(),
                ),
            )
            .order_by(*params["directory_ordering"], "name")
        )
        return dirs

    def paginate(self, params, subdirectories, files):
        """Paginate direcories and files together."""
        limit = params["limit"]
        offset = params["offset"]

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
        subdirs = directories.exclude(name="")  # exclude current dir
        if name := params.get("name"):
            subdirs = subdirs.filter(name__icontains=name)
        if params["published"] is True:
            subdirs = subdirs.exclude(published_file_count=0)
        elif params["published"] is False:
            subdirs = subdirs.exclude(file_count=F("published_file_count"))
        return subdirs

    def get_parent_data(self, params, directories):
        """Aggregate totals for parent directory."""
        file_count = sum(d.get("file_count", 0) for d in directories)
        published_file_count = sum(d.get("published_file_count", 0) for d in directories)
        size = sum(d.get("size", 0) for d in directories)
        created = min((d.get("created") for d in directories), default=None)
        modified = max((d.get("modified") for d in directories), default=None)
        return {
            "directory": {
                "name": params["path"].split("/")[-2],
                "pathname": params["path"],
                "file_count": file_count,
                "published_file_count": published_file_count,
                "size": size,
                "created": created,
                "modified": modified,
            }
        }

    def get_storage(self, params):
        """Return storage project common for all subdirectories and files."""
        return FileStorage.objects.get(id=params.get("storage_id"))

    def get_dataset_metadata(self, params, matching_subdirs, files):
        """Fetch dataset-specific file/directory metadata as key-value pairs."""

        metadata = {}
        dataset = params.get("dataset")
        if dataset and not params.get("exclude_dataset"):
            file_fields = params.get("file_fields")
            if (not file_fields) or ("dataset_metadata" in file_fields):
                # Get file metadata with file id as key.
                # Files may be or File instances or .values() dicts.
                file_metadata = (
                    get_file_metadata_model()
                    .objects.filter(file_set__dataset_id=dataset)
                    .prefetch_related("file_type")
                    .distinct("file_id")
                    .in_bulk([get_attr_or_item(f, "id") for f in files], field_name="file_id")
                )
                metadata["file_metadata"] = file_metadata

            directory_fields = params.get("directory_fields")
            if (not directory_fields) or ("dataset_metadata" in directory_fields):
                # Get directory metadata, directory path as key.
                pathnames = [params["path"]]
                pathnames += [d["pathname"] for d in matching_subdirs]
                directory_metadata_list = get_directory_metadata_model().objects.filter(
                    file_set__dataset_id=dataset, pathname__in=pathnames
                )
                directory_metadata = {d.pathname: d for d in directory_metadata_list}
                metadata["directory_metadata"] = directory_metadata
        return metadata

    @swagger_auto_schema(responses={200: DirectorySerializer})
    def list(self, request, *args, **kwargs):
        """Directory content view."""
        params = self.query_params
        with cachalot_toggle(enabled=params["pagination"]):
            directories = self.get_directories(params)
            parent_data = {}
            if params.get("include_parent"):
                parent_data = self.get_parent_data(params, directories)

            # Evaluate all subdirectories into a list so they can be
            # counted and sliced in a single DB query.
            matching_subdirs = list(self.get_matching_subdirectories(params, directories))
            files = self.get_directory_files(params)

            pagination_data = {}
            if params.get("pagination"):
                paginated = self.paginate(params, matching_subdirs, files)
                matching_subdirs = paginated["directories"]
                files = paginated["files"]
                pagination_data = self.get_pagination_data(request, params, paginated)

            dataset_metadata = self.get_dataset_metadata(params, matching_subdirs, files)

            instance = {
                **parent_data,
                "directories": matching_subdirs,
                "files": files,
            }

            # all directories and files have same project, pass it through context
            storage = self.get_storage(params)
            serialized_data = DirectorySerializer(
                instance,
                context={
                    "include_nulls": self.include_nulls,
                    "request": self.request,
                    "directory_fields": params.get("directory_fields"),
                    "file_fields": params.get("file_fields"),
                    "count_published": params["count_published"],
                    "storage": storage,
                    **dataset_metadata,  # add file and directory metadata to context
                },
            ).data
            results = serialized_data
            if params.get("pagination"):
                results = {"results": serialized_data}

            # empty results may be due to pagination, remove parent dir if it does not actually exist
            if (
                "directory" in results
                and not serialized_data["directories"]
                and not serialized_data["files"]
                and not directories.exists()
            ):
                del results["directory"]
            return Response({**pagination_data, **results})
