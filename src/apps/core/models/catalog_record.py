import uuid

from .abstracts import AbstractBaseModel
from .data_catalog import AccessRights, DataCatalog
from .contract import Contract
from django.db import models
from django.contrib.postgres.fields import ArrayField, HStoreField

from apps.core.models.concepts import Theme, Language, FieldOfScience
from simple_history.models import HistoricalRecords



class CatalogRecord(AbstractBaseModel):
    """A record in a catalog, describing the registration of a single resource.

    RDF Class: dcat:CatalogRecord

    Source: [DCAT Version 3, Draft 11](https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog_Record)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_catalog = models.ForeignKey(
        DataCatalog,
        on_delete=models.DO_NOTHING,
        related_name="records",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        related_name="records",
        null=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)


class Dataset(CatalogRecord, AbstractBaseModel):
    """A collection of data available for access or download in one or many representations.

    RDF Class: dcat:Dataset

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Dataset
    """

    persistent_identifier = models.CharField(max_length=255, null=True, blank=True)
    issued = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of formal issuance (e.g., publication) of the resource.",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    description = HStoreField(max_length=255, null=True, blank=True)

    keyword = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    other_identifiers = ArrayField(
        models.CharField(max_length=255), default=list, blank=True
    )
    language = models.ManyToManyField(
        Language, related_name="datasets", blank=True
    )
    theme = models.ManyToManyField(
        Theme, related_name="datasets", blank=True
    )
    field_of_science = models.ManyToManyField(
        FieldOfScience, related_name="datasets", blank=True
    )

    access_rights = models.ForeignKey(
        AccessRights,
        on_delete=models.SET_NULL,
        related_name="datasets",
        null=True,
    )
    is_deprecated = models.BooleanField(default=False)
    cumulation_started = models.DateTimeField(null=True, blank=True)
    cumulation_ended = models.DateTimeField(null=True, blank=True)
    first = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_version",
    )
    last = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="last_version",
    )
    previous = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next",
    )
    replaces = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaced_by",
    )
    history = HistoricalRecords(m2m_fields=(language, theme, field_of_science))

    def delete(self, *args, **kwargs):
        if self.access_rights:
            self.access_rights.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)
