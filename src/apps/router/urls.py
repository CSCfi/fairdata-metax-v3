from core.views import DatasetActorViewSet
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from apps.actors.views import ActorViewSet, OrganizationViewSet
from apps.core.views import (
    DataCatalogView,
    DatasetDirectoryViewSet,
    DatasetFilesViewSet,
    DatasetViewSet,
    MetadataProviderViewSet,
    PublisherViewSet,
)
from apps.files.views import DirectoryViewSet, FileViewSet
from apps.refdata.models import reference_data_models
from apps.refdata.views import get_viewset_for_model

router = DefaultRouter(trailing_slash=False)

# actors app
router.register(
    "organizations?",
    OrganizationViewSet,
)
# core app
router.register(r"data-catalogs?", DataCatalogView, basename="datacatalog")
router.register(r"datasets?", DatasetViewSet, basename="dataset")
router.register(
    r"datasets?/(?P<dataset_id>[^/.]+)/files",
    DatasetFilesViewSet,
    basename="dataset_files",
)
router.register(
    r"datasets?/(?P<dataset_id>[^/.]+)/directories",
    DatasetDirectoryViewSet,
    basename="dataset_directories",
)
# router.register(r"dataset-actors?", DatasetActorViewSet, basename="dataset-actor")
router.register(r"metadata-providers?", MetadataProviderViewSet, basename="metadata-provider")
router.register(r"publishers?", PublisherViewSet, basename="publisher")
# files app
router.register(r"files?", FileViewSet, basename="file")
router.register(r"directories", DirectoryViewSet, basename="directory")
# Refdata app
for model in reference_data_models:
    router.register(
        f"reference-data/{model.get_model_url()}",
        get_viewset_for_model(model),
    )
# Nested routes
dataset_router = routers.NestedSimpleRouter(router, r"datasets?", lookup="dataset")
dataset_router.register(r"actors", DatasetActorViewSet, basename="dataset-actors")
urlpatterns = [path("", include(router.urls)), path("", include(dataset_router.urls))]
