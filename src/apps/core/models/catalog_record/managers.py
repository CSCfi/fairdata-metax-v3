from typing import Self
from django.db import models
from django.utils.translation import gettext as _

from apps.common.models import CustomSoftDeletableManager, CustomSoftDeletableQuerySet
from apps.core.models.access_rights import AccessTypeChoices

rems_dataset_filter = models.Q(
    state="published",
    access_rights__access_type__url=AccessTypeChoices.PERMIT,
    access_rights__rems_approval_type__isnull=False,
    data_catalog__rems_enabled=True,
    metadata_owner__admin_organization__isnull=False,
)


class DatasetQuerySetMixin:
    def rems_datasets(self, exclude=False) -> Self:
        """Filter datasets that have the fields required by REMS set."""
        if exclude:
            return self.exclude(rems_dataset_filter)
        return self.filter(rems_dataset_filter)


class DatasetQuerySet(DatasetQuerySetMixin, models.QuerySet):
    pass


class SoftDeletableDatasetQuerySet(DatasetQuerySetMixin, CustomSoftDeletableQuerySet):
    pass


DatasetManager = models.Manager.from_queryset(DatasetQuerySet)

SoftDeletableDatasetManager = CustomSoftDeletableManager.from_queryset(
    SoftDeletableDatasetQuerySet
)
