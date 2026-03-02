# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import logging
from datetime import datetime, timezone
from typing import List

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from django.core.cache import caches
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet, Value
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.http import parse_http_date
from django.utils.translation import gettext_lazy as _
from drf_yasg.openapi import TYPE_STRING, Parameter, Response, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, response, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import JSONRenderer
from rest_framework.reverse import reverse

from apps.common.helpers import ensure_dict, omit_empty
from apps.common.serializers.serializers import (
    FlushQueryParamsSerializer,
    IncludeRemovedQueryParamsSerializer,
)
from apps.common.views import CommonModelViewSet
from apps.core.cache import DatasetSerializerCache
from apps.core.models.catalog_record import Dataset, FileSet
from apps.core.models.data_catalog import DataCatalog
from apps.core.models.legacy_converter import LegacyDatasetConverter
from apps.core.permissions import DataCatalogAccessPolicy, DatasetAccessPolicy
from apps.core.renderers import DataciteXMLRenderer, FairdataDataciteXMLRenderer
from apps.core.serializers import DatasetSerializer
from apps.core.serializers.contact_serializer import (
    ContactResponseSerializer,
    ContactRolesSerializer,
    ContactSerializer,
)
from apps.core.serializers.dataset_allowed_actions import (
    DatasetAllowedActionsQueryParamsSerializer,
)
from apps.core.serializers.dataset_metrics_serializer import DatasetMetricsQueryParamsSerializer
from apps.core.serializers.dataset_serializer import (
    DatasetAggregationQueryParamsSerializer,
    DatasetFieldsQueryParamsSerializer,
    ExpandCatalogQueryParamsSerializer,
    FacetLanguageQueryParamsSerializer,
    ExpandUserQueryParamsSerializer,
    LatestVersionQueryParamsSerializer,
)
from apps.core.serializers.legacy_serializer import LegacyDatasetConversionValidationSerializer
from apps.core.services import MetaxV2Client, PIDMSClient
from apps.core.views.dataset_filters import DatasetFilter
from apps.files.models import File
from apps.files.serializers import DirectorySerializer
from apps.files.views.directory_view import DirectoryCommonQueryParams, DirectoryViewSet
from apps.files.views.file_view import BaseFileViewSet, FileCommonFilterset
from apps.rems.rems_service import REMSService
from apps.rems.serializers import (
    ApplicationBaseSerializer,
    ApplicationCountsSerializer,
    ApplicationDataSerializer,
)

from .dataset_aggregation import aggregate_queryset

logger = logging.getLogger(__name__)
serialized_datasets_cache = caches["serialized_datasets"]


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        responses={
            403: Response(
                "unauthorized",
            )
        }
    ),
)
class DatasetViewSet(CommonModelViewSet):
    filter_actions = ["list", "aggregates"]
    query_serializers = [
        {"class": LatestVersionQueryParamsSerializer, "actions": ["list", "aggregates"]},
        {
            "class": ExpandCatalogQueryParamsSerializer,
            "actions": ["list", "retrieve", "create", "update", "partial_update"],
        },
        {
            "class": ExpandUserQueryParamsSerializer,
            "actions": ["list", "retrieve", "create", "update", "partial_update"],
        },
        {
            "class": DatasetAllowedActionsQueryParamsSerializer,
            "actions": ["retrieve", "list", "create", "update", "partial_update", "revisions"],
        },
        {
            "class": DatasetMetricsQueryParamsSerializer,
            "actions": ["retrieve", "list", "create", "update", "partial_update", "revisions"],
        },
        {
            "class": IncludeRemovedQueryParamsSerializer,
            "actions": [
                "list",
                "retrieve",
                "update",
                "partial_update",
                "contact",
                "contact_roles",
            ],
        },
        {
            "class": FlushQueryParamsSerializer,
            "actions": ["destroy"],
        },
        {
            "class": DatasetFieldsQueryParamsSerializer,
            "actions": ["list", "retrieve"],
        },
        {
            "class": DatasetAggregationQueryParamsSerializer,
            "actions": ["aggregates"],
        },
        {"class": FacetLanguageQueryParamsSerializer, "actions": ["list"]},
    ]
    access_policy = DatasetAccessPolicy
    serializer_class = DatasetSerializer

    queryset = Dataset.available_objects.prefetch_related(
        *Dataset.common_prefetch_fields
    ).annotate(is_prefetched=Value(True))
    queryset_include_removed = Dataset.all_objects.prefetch_related(
        *Dataset.common_prefetch_fields
    ).annotate(is_prefetched=Value(True))

    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "options"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.query_params.get("latest_versions"):
            # Return only the latest dataset versions available for the current user.
            # By default, includes drafts if the user can see them.
            if self.request.GET.get("state") == Dataset.StateChoices.PUBLISHED:
                # Ignore drafts to allow users to see the latest published version
                # with ?latest_versions=true&state=published
                # even if there exists a later draft.
                available_datasets = self.get_queryset(only_published=True)
            else:
                available_datasets = self.get_queryset()

            return queryset.filter(
                ~Exists(
                    available_datasets.filter(
                        dataset_versions_id=OuterRef("dataset_versions_id"),
                        dataset_versions_order__gt=OuterRef("dataset_versions_order"),
                    )
                )
            )
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                name="format",
                in_="query",
                description="Metadata output format.",
                type=TYPE_STRING,
                enum=(
                    JSONRenderer.format,
                    DataciteXMLRenderer.format,
                    FairdataDataciteXMLRenderer.format,
                ),
            )
        ]
    )
    @action(
        detail=True,
        url_path="metadata-download",
        renderer_classes=[JSONRenderer, DataciteXMLRenderer, FairdataDataciteXMLRenderer],
    )
    def metadata_download(self, request, pk=None):
        """Return dataset metadata as a file attachment."""
        try:
            obj = self.get_object()
        except Http404:
            # Use Django HttpResponse directly to avoid renderer
            return HttpResponse("Dataset not found.", status=404, content_type="text/plain")

        serializer = self.serializer_class
        serializer_context = self.get_serializer_context()
        extension = "json"

        data = None
        if request.accepted_renderer.media_type == "application/xml":
            extension = "xml"
            data = obj  # XML renderer takes dataset objects
        else:
            data = serializer(obj, context=serializer_context).data

        return response.Response(
            data,
            headers={"Content-Disposition": f"attachment; filename={pk}-metadata.{extension}"},
        )

    def get_queryset(self, only_published=False):
        include_all_datasets = self.query_params.get("include_removed") or self.query_params.get(
            "flush"
        )
        qs: QuerySet
        if include_all_datasets:
            qs = self.queryset_include_removed
        else:
            qs = self.queryset

        if self.request.method == "GET":
            # Prefetch Dataset.dataset_versions.datasets to DatasetVersions._datasets
            # but only for read-only requests to avoid having to invalidate the cached value
            qs = qs.prefetch_related(Dataset.get_versions_prefetch())

            if timestamp := self.request.META.get("HTTP_IF_MODIFIED_SINCE"):
                try:
                    date = datetime.fromtimestamp(parse_http_date(timestamp), timezone.utc)
                except Exception:
                    raise exceptions.ValidationError(
                        {
                            "headers": {
                                "If-Modified-Since": "Bad value. If-Modified-Since supports only RFC 2822 datetime format."
                            }
                        }
                    )
                if date:
                    qs = qs.filter(modified__gt=date)

        if only_published:
            # Optimization allowing skipping access policy when only published datasets are needed
            qs = qs.filter(state=Dataset.StateChoices.PUBLISHED)
        else:
            qs = self.access_policy.scope_queryset(self.request, qs)
        return qs

    def get_serializer(self, *args, cached_instances=[], cache_autocommit=True, **kwargs):
        serializer_cache = None
        # Use cached fields for serialization of datasets in cached_instances
        serializer_cache = DatasetSerializerCache(cached_instances, autocommit=cache_autocommit)

        return super().get_serializer(*args, cache=serializer_cache, **kwargs)

    def list(self, request, *args, **kwargs):
        """List datasets."""
        only_published = request.GET.get("state") == Dataset.StateChoices.PUBLISHED
        queryset = self.filter_queryset(self.get_queryset(only_published=only_published))

        # Defer prefetching until after pagination is done
        # and we know which datasets are in serialized datasets cache
        prefetches = queryset._prefetch_related_lookups
        queryset = queryset.prefetch_related(None)
        queryset = queryset.prefetch_related(*Dataset.permissions_prefetch_fields)

        page = self.paginate_queryset(queryset)

        datasets: List[Dataset]
        if page is None:
            datasets = queryset.all()
        else:
            datasets = page

        list_serializer = self.get_serializer(
            datasets, cached_instances=datasets, cache_autocommit=False, many=True
        )
        dataset_serializer: DatasetSerializer = list_serializer.child
        cache = dataset_serializer.cache
        if cache and settings.DEBUG_DATASET_CACHE:
            logger.info(f"Datasets in cache: {len(cache.values)}/{len(datasets)}")
        dataset_serializer.apply_partial_prefetch(datasets, prefetches)

        serialized_data = list_serializer.data  # Run serialization
        if cache:
            cache.commit_changed_to_source()  # Commit updated serializations to cache

        if page is None:
            return response.Response(serialized_data)
        else:
            return self.get_paginated_response(serialized_data)

    def get_object(self) -> Dataset:
        if self.request.method not in ("GET", "OPTIONS"):
            # Lock dataset row for the duration of the transaction
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            Dataset.lock_for_update(id=self.kwargs[lookup_url_kwarg])

        obj: Dataset = super().get_object()
        return obj

    def _get_object_with_deferred_prefetch(self):
        """Get object without triggering prefetch."""
        queryset = self.get_queryset()

        # Defer prefetching until we know if dataset is in cache
        prefetches = queryset._prefetch_related_lookups
        queryset = queryset.prefetch_related(None)
        queryset = queryset.prefetch_related(*Dataset.permissions_prefetch_fields)

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj, prefetches

    def retrieve(self, request, *args, **kwargs):
        """Retrieve single dataset. Modified for cache use."""
        instance, prefetches = self._get_object_with_deferred_prefetch()

        serializer: DatasetSerializer = self.get_serializer(instance, cached_instances=[instance])
        if (cache := serializer.cache) and settings.DEBUG_DATASET_CACHE:
            logger.info(f"Dataset in cache: {instance.id in cache.values}")

        serializer.apply_partial_prefetch([instance], prefetches)

        return response.Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        """Create a new version of a published dataset.

        The new version is created as a draft.
        """
        dataset: Dataset = self.get_object()
        new_version = dataset.create_new_version()
        serializer = self.get_serializer(new_version)
        data = serializer.data
        new_version.signal_update(created=True)

        if settings.METAX_V2_INTEGRATION_ENABLED:
            # New version is a initially a draft that is not synced to V2,
            # so V2 does not know it exists. Mark original as having been
            # updated in V3 to prevent creating more versions in V2.
            MetaxV2Client().update_api_meta(dataset)

        return response.Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="create-draft")
    def create_draft(self, request, pk=None):
        """Create a draft dataset from a published dataset.

        The changes in the draft can be applied to the
        published dataset using the publish endpoint of the draft.
        """
        dataset: Dataset = self.get_object()
        draft = dataset.create_new_draft()
        data = self.get_serializer(draft).data
        draft.signal_update(created=True)
        return response.Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="create-preservation-version")
    def create_preservation_version(self, request, pk=None):
        """Create preservation version of a dataset in PAS process."""
        dataset: Dataset = self.get_object()
        new_version = dataset.create_preservation_version()
        serializer = self.get_serializer(new_version)
        data = serializer.data
        new_version.signal_update(created=True)
        return response.Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a dataset.

        - If dataset is a new draft, changes its state to "published".
        - If dataset is a draft of an existing published dataset,
          updates the published dataset with changes from the draft
          and deletes the draft.
        """
        dataset: Dataset = self.get_object()
        dataset.api_version = 3
        published_dataset = dataset.publish()
        data = self.get_serializer(published_dataset).data
        published_dataset.signal_update()
        return response.Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=ContactSerializer(), responses={200: ContactResponseSerializer}
    )
    @action(detail=True, methods=["POST"])
    def contact(self, request, pk=None):
        """Send email to dataset actors with specific role."""
        dataset: Dataset = self.get_object()
        serializer = ContactSerializer(data=request.data, context={"dataset": dataset})
        serializer.is_valid(raise_exception=True)
        mail_count = serializer.save()
        response_msg = ContactResponseSerializer(instance={"recipient_count": mail_count}).data
        return response.Response(response_msg, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: ContactRolesSerializer})
    @contact.mapping.get
    def contact_roles(self, request, pk=None):
        """Determine for each role if there are any email addresses for that role."""
        dataset: Dataset = self.get_object()
        serializer = ContactRolesSerializer(instance=dataset)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=Schema(type="object"), responses={200: DatasetSerializer})
    @action(detail=False, methods=["POST"])
    def convert_from_legacy(self, request):
        """Convert V1 or V2 dataset json into V3 json format.

        Accepts a V1 or V2 dataset json as the request body.
        Dataset fields are mapped to V3 format and the resulting dataset
        json is validated and then returned. If any errors found are found,
        the response will contain an additional "errors" object
        describing the errrors.

        Note that no permission checking is done and the dataset json
        may need additional changes to be ready for publishing.
        """
        data = None
        errors = {}
        with transaction.atomic():
            try:
                ensure_dict(request.data)
                try:
                    converter = LegacyDatasetConverter(
                        dataset_json=request.data, convert_only=True
                    )
                    data = omit_empty(converter.convert_dataset(), recurse=True)
                    if invalid := converter.get_invalid_values_by_path():
                        errors["invalid"] = invalid
                    if fixed := converter.get_fixed_values_by_path():
                        errors["fixed"] = fixed
                    serializer = LegacyDatasetConversionValidationSerializer(
                        data=data, context={"dataset": None}
                    )
                    serializer.is_valid(raise_exception=True)
                except serializers.ValidationError as e:
                    if data:
                        detail = e.detail
                        if not isinstance(e.detail, dict):
                            detail = {"error": detail}
                        errors.update(detail)
                    else:
                        raise e
                except (AttributeError, ValueError) as e:
                    # Catch unhandled cases where input data has wrong type
                    logger.warning(f"convert_from_legacy failed: {e}")
                    return response.Response(
                        "There was an error converting the dataset.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            finally:
                transaction.set_rollback(True)  # Ensure no side effects are left in DB
        if errors:
            data["errors"] = errors
        return response.Response(data, status=status.HTTP_200_OK)

    def _check_allow_create_datasets_in_catalog(self, catalog: DataCatalog):
        """Raise error if request user is not allowed to create datasets in the catalog."""
        if not DataCatalogAccessPolicy().query_object_permission(
            user=self.request.user, object=catalog, action="<op:create_dataset>"
        ):
            raise exceptions.PermissionDenied(
                "You are not allowed to create datasets in this data catalog."
            )

    def _check_allow_update_datasets_in_catalog(self, catalog: DataCatalog):
        """Raise error if request user is not allowed to update datasets in the catalog."""
        if not DataCatalogAccessPolicy().query_object_permission(
            user=self.request.user, object=catalog, action="<op:update_dataset>"
        ):
            raise exceptions.PermissionDenied(
                "You are not allowed to update datasets in this data catalog."
            )

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise NotAuthenticated("You must be authenticated to perform this action.")

        catalog: DataCatalog = serializer._validated_data.get("data_catalog")
        if catalog:
            self._check_allow_create_datasets_in_catalog(catalog)
        dataset: Dataset = serializer.save(system_creator=self.request.user)
        dataset.signal_update(created=True)

    def perform_update(self, serializer):
        catalog: DataCatalog = serializer._validated_data.get("data_catalog")
        if catalog and not serializer.instance.data_catalog:
            # Setting catalog of a draft needs permission to create datasets in the catalog
            self._check_allow_create_datasets_in_catalog(catalog)
        dataset: Dataset = serializer.save()
        if (
            dataset.state == Dataset.StateChoices.PUBLISHED
            and dataset.pid_generated_by_fairdata
            and dataset.generate_pid_on_publish == "DOI"
        ):
            PIDMSClient().update_doi_dataset(dataset.id, dataset.persistent_identifier)
        dataset.signal_update()

    @action(detail=False)
    def aggregates(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        aggregates = aggregate_queryset(queryset, request)
        return response.Response(aggregates, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        """Called by 'destroy' action."""
        flush = self.query_params["flush"]
        if flush and not DatasetAccessPolicy().query_object_permission(
            user=self.request.user, object=instance, action="<op:flush>"
        ):
            raise exceptions.PermissionDenied()
        instance.delete(soft=not flush)

    def get_extra_action_url_map(self):
        url_map = super().get_extra_action_url_map()

        if self.detail:
            url_map["Preservation"] = reverse(
                "dataset-preservation-detail",
                self.args,
                {"dataset_pk": self.kwargs["pk"]},
                request=self.request,
            )

        return url_map

    def check_rems_request(self, request, dataset: Dataset, require_fairdata_user=True):
        if not settings.REMS_ENABLED:
            raise exceptions.MethodNotAllowed(method=request.method, detail="REMS is not enabled")
        if require_fairdata_user and not getattr(request.user, "fairdata_username", None):
            raise exceptions.PermissionDenied(
                detail="You need to be logged in as a Fairdata user."
            )
        if not dataset.is_rems_dataset:
            raise exceptions.ValidationError(detail="Dataset is not enabled for REMS.")

    @action(methods=["get"], detail=True, url_path="rems-applications")
    def list_rems_applications(self, request, pk=None):
        """Get list of dataset REMS applications by logged in user."""
        dataset = self.get_object()
        self.check_rems_request(request, dataset)
        service = REMSService()
        data = service.get_user_applications_for_dataset(request.user, dataset)
        return response.Response(data, status=status.HTTP_200_OK)

    @list_rems_applications.mapping.post
    def create_rems_application(self, request, pk=None):
        """Create and submit dataset REMS application for logged in user."""
        dataset = self.get_object()
        self.check_rems_request(request, dataset)
        service = REMSService()
        serializer = ApplicationDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = service.create_application_for_dataset(
            request.user,
            dataset,
            accept_licenses=serializer.validated_data["accept_licenses"],
            field_values=serializer.validated_data["field_values"],
        )
        return response.Response(data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="rems-applications/(?P<application_id>[0-9]+)")
    def get_rems_application(self, request, pk: str, application_id: str):
        """Get dataset REMS application by id for logged in user."""
        dataset = self.get_object()
        self.check_rems_request(request, dataset)
        service = REMSService()
        application = service.get_user_application_for_dataset(
            request.user, dataset, application_id=int(application_id)
        )
        if not application:
            raise Http404("Application not found for dataset")
        return response.Response(application, status=status.HTTP_200_OK)

    @action(
        methods=["post"],
        detail=True,
        url_path="rems-applications/(?P<application_id>[0-9]+)/submit",
    )
    def submit_rems_application(self, request, pk: str, application_id: str):
        """Submit draft or returned REMS application with new data."""
        dataset = self.get_object()
        self.check_rems_request(request, dataset)
        service = REMSService()
        serializer = ApplicationDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = service.submit_application_for_dataset(
            request.user,
            dataset=dataset,
            application_id=int(application_id),
            accept_licenses=serializer.validated_data["accept_licenses"],
            field_values=serializer.validated_data["field_values"],
        )
        return response.Response(data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="rems-entitlements")
    def list_rems_entitlements(self, request, pk=None):
        """List dataset REMS entitlements for logged in user."""
        dataset = self.get_object()
        self.check_rems_request(request, dataset)
        service = REMSService()
        data = service.get_user_entitlements_for_dataset(request.user, dataset)
        return response.Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: ApplicationBaseSerializer()})
    @action(methods=["get"], detail=True, url_path="rems-application-base")
    def get_rems_application_base(self, request, pk=None):
        """Get the licenses and forms needed by REMS applications for the dataset."""
        dataset = self.get_object()
        self.check_rems_request(request, dataset)
        service = REMSService()
        application_base = service.get_application_base_for_dataset(dataset)
        data = ApplicationBaseSerializer(instance=application_base).data
        return response.Response(data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="rems-check")
    def get_rems_check(self, request, pk=None):
        """Check values required for dataset to be valid for REMS."""
        dataset = self.get_object()
        return response.Response(dataset.rems_check(), status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: ApplicationCountsSerializer()})
    @action(methods=["get"], detail=True, url_path="rems-application-counts")
    def get_rems_application_counts(self, request, pk=None):
        """Count submitted and approbed REMS applications for dataset."""
        dataset = self.get_object()
        # GET requests are allowed for everyone in the access policy so
        # we need to explicitly deny users who do should not have access to this endpoint.
        if not dataset.has_permission_to_edit(request.user):
            raise PermissionDenied()

        self.check_rems_request(request, dataset, require_fairdata_user=False)

        service = REMSService()
        serializer = ApplicationCountsSerializer(
            instance=service.get_dataset_application_counts(dataset)
        )
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class DatasetDirectoryViewSet(DirectoryViewSet):
    """API for browsing directories of a dataset."""

    # Omit dataset-specific parameters from API, set them manually for the view
    query_serializers = [
        {
            "class": DirectoryCommonQueryParams,
        }
    ]

    def validate_query_params(self):
        """Parse view query parameters."""
        super().validate_query_params()

        # Dataset id comes from route, file storage is determined from dataset
        dataset_id = self.kwargs["dataset_id"]
        params = {}
        params["dataset"] = dataset_id
        params["exclude_dataset"] = False
        params["include_all"] = False
        try:
            file_set = FileSet.objects.get(dataset_id=dataset_id)
            storage = file_set.storage
            params["storage_id"] = storage.id
        except FileSet.DoesNotExist:
            raise exceptions.NotFound("No fileset has been set for this dataset.")
        self.query_params.update(params)

    @swagger_auto_schema(responses={200: DirectorySerializer})
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)


class DatasetFilesViewSet(BaseFileViewSet):
    """API for listing dataset files."""

    filterset_class = FileCommonFilterset

    def get_queryset(self):
        # path parameters are not available on drf-yasg inspection
        if getattr(self, "swagger_fake_view", False):
            return File.objects.none()

        dataset_id = self.kwargs["dataset_id"]
        files = super().get_queryset()
        file_set: FileSet
        try:
            file_set = FileSet.objects.get(dataset=dataset_id)
        except FileSet.DoesNotExist:
            return files.none()
        return files.filter(file_sets=file_set.id, storage=file_set.storage)
