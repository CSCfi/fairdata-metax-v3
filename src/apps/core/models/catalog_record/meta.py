import datetime
import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.common.copier import ModelCopier
from apps.common.models import AbstractBaseModel
from apps.core.models.concepts import IdentifierType
from apps.core.models.data_catalog import DataCatalog
from apps.core.models.preservation import Preservation

logger = logging.getLogger(__name__)


class MetadataProvider(AbstractBaseModel):
    """Information about the creator of the metadata, and the associated organization.

    Attributes:
        user(django.contrib.auth.models.AbstractUser): User ForeignKey relation
        organization(models.CharField): Organization id
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.CharField(max_length=512)


class OtherIdentifier(AbstractBaseModel):
    """Other identifier that dataset has in other services.

    Attributes:
        identifier_type(IdentifierType): IdentifierType ForeignKey relation
        notation(models.CharField): Identifier
        old_notation(models.CharField): Legacy notation value from V1-V2 metax
    """

    copier = ModelCopier(copied_relations=[], parent_relations=["dataset"])

    notation = models.CharField(max_length=512)
    old_notation = models.CharField(max_length=512, blank=True, null=True)
    identifier_type = models.ForeignKey(
        IdentifierType,
        on_delete=models.CASCADE,
        related_name="dataset_identifiers",
        blank=True,
        null=True,
    )
    # ToDo: Provider


class CatalogRecord(AbstractBaseModel):
    """A record in a catalog, describing the registration of a single resource.

    RDF Class: dcat:CatalogRecord

    Source: [DCAT Version 3, Draft 11](https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog_Record)

    Attributes:
        data_catalog(DataCatalog): DataCatalog ForeignKey relation
        metadata_owner(MetadataProvider): MetadataProvider ForeignKey relation
        preservation(Preservation): Preservation OneToOne relation
        last_modified_by(Actor): Actor ForeignKey relation
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_catalog = models.ForeignKey(
        DataCatalog, on_delete=models.DO_NOTHING, related_name="datasets", null=True, blank=True
    )
    preservation = models.OneToOneField(
        Preservation, on_delete=models.CASCADE, related_name="dataset", null=True, blank=True
    )

    metadata_owner = models.ForeignKey(
        MetadataProvider,
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )

    created = models.DateTimeField(default=timezone.now, editable=False)
    modified = models.DateTimeField(default=timezone.now)

    api_version = models.SmallIntegerField(default=3)

    def __str__(self):
        return str(self.id)

    class Meta(AbstractBaseModel.Meta):
        abstract = True
