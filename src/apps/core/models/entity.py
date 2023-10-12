from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.models import AbstractBaseModel

from .concepts import ResourceType


class Entity(AbstractBaseModel):
    """An entity related to the dataset or provenance.

    Source: http://www.w3.org/ns/prov#Entity
    """

    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}', blank=True, null=True)
    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', blank=True, null=True
    )
    entity_identifier = models.CharField(max_length=512, blank=True, null=True)
    type = models.ForeignKey(ResourceType, on_delete=models.CASCADE, blank=True, null=True)
    provenance = models.ForeignKey(
        "Provenance",
        on_delete=models.CASCADE,
        related_name="used_entity",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = "Entities"
