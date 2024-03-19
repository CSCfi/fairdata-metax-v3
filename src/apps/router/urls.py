from django.conf import settings
from django.urls import include, path, re_path
from rest_framework_nested import routers

from apps.actors.views import OrganizationViewSet
from apps.core import views as core_views
from apps.download import views as download_views
from apps.files.views import DirectoryViewSet, FileViewSet
from apps.refdata.models import reference_data_models
from apps.refdata.views import get_viewset_for_model
from apps.users.views import UserViewSet

from .router import CommonRouter

router = CommonRouter(trailing_slash=False)

# actors app
router.register(
    "organizations",
    OrganizationViewSet,
)
# core app
router.register(r"contracts", core_views.ContractViewSet, basename="contract")
router.register(r"data-catalogs", core_views.DataCatalogView, basename="datacatalog")
router.register(r"datasets", core_views.DatasetViewSet, basename="dataset")

router.register(
    r"datasets/(?P<dataset_id>[^/.]+)/files",
    core_views.DatasetFilesViewSet,
    basename="dataset-files",
)
router.register(
    r"datasets/(?P<dataset_id>[^/.]+)/directories",
    core_views.DatasetDirectoryViewSet,
    basename="dataset-directories",
)

# router.register(r"dataset-actors", DatasetActorViewSet, basename="dataset-actor")
router.register(r"migrated-datasets", core_views.LegacyDatasetViewSet, basename="migrated-dataset")

# download app
router.register(r"download", download_views.DownloadViewSet, basename="download")

# files app
router.register(r"files", FileViewSet, basename="file")
router.register(r"directories", DirectoryViewSet, basename="directory")
# Refdata app
for model in reference_data_models:
    router.register(
        f"reference-data/{model.get_model_url()}",
        get_viewset_for_model(model),
    )
# Nested routes
dataset_router = routers.NestedSimpleRouter(router, r"datasets", lookup="dataset")
dataset_router.register(r"actors", core_views.DatasetActorViewSet, basename="dataset-actors")
dataset_router.register(r"provenance", core_views.ProvenanceViewSet, basename="dataset-provenance")
dataset_router.register(
    r"access-rights",
    core_views.AccessRightsViewSet,
    basename="dataset-access-rights",
)
# Users list
if settings.ENABLE_USERS_VIEW:
    router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    # Custom patterns
    re_path(
        r"^datasets/(?P<dataset_pk>[^/.]+)/preservation$",
        core_views.PreservationViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "put": "update"}
        ),
        name="dataset-preservation-detail",
    ),
    path("", include(router.urls)),
    path("", include(dataset_router.urls)),
]
