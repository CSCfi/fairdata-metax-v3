from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.models import AbstractBaseModel


class DataService(AbstractBaseModel):
    """
    Controlled list of DAAS "data services" exposed under Data Catalog expansion.

    Seeded from `src/apps/core/management/initial_data/data_services.json`.
    """

    id = models.CharField(max_length=255, primary_key=True)
    catalog = models.ForeignKey(
        "DataCatalog", on_delete=models.CASCADE, related_name="data_services"
    )
    pref_label = HStoreField(
        blank=True,
        null=True,
        help_text=_('example: {"fi":"otsikko","en":"title"}'),
    )

    class Meta:
        verbose_name = "data service"
        verbose_name_plural = "data services"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.id

