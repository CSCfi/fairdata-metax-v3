import uuid

from .abstracts import AbstractBaseModel
from .data_catalog import DataCatalog
from django.db import models


class CatalogRecord(AbstractBaseModel):
    """A record in a catalog, describing the registration of a single resource.

    RDF Class: dcat:CatalogRecord

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog_Record
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_catalog = models.ForeignKey(
        DataCatalog,
        on_delete=models.DO_NOTHING,
        related_name="records",
    )

    def __str__(self):
        return str(self.id)