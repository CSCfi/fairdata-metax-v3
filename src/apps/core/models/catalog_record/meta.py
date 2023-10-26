import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from simple_history.models import HistoricalRecords

from apps.actors.models import Actor
from apps.common.models import AbstractBaseModel
from apps.core.models.concepts import IdentifierType
from apps.core.models.contract import Contract
from apps.core.models.data_catalog import DataCatalog

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
        contract(Contract): Contract ForeignKey relation
        history(HistoricalRecords): Historical model changes
        metadata_owner(MetadataProvider): MetadataProvider ForeignKey relation
        preservation_identifier(models.CharField): PAS identifier
        last_modified_by(Actor): Actor ForeignKey relation
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
        blank=True,
    )
    history = HistoricalRecords()

    # TODO make this field required when purging migrations
    metadata_owner = models.ForeignKey(
        MetadataProvider,
        on_delete=models.CASCADE,
        related_name="metadata_owner",
        null=True,
    )
    preservation_identifier = models.CharField(max_length=512, null=True, blank=True)
    last_modified_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )

    class PreservationState(models.IntegerChoices):
        NONE = -1
        INITIALIZED = 0
        GENERATING_TECHNICAL_METADATA = 10
        TECHNICAL_METADATA_GENERATED = 20
        TECHNICAL_METADATA_GENERATED_FAILED = 30
        INVALID_METADATA = 40
        METADATA_VALIDATION_FAILED = 50
        VALIDATED_METADATA_UPDATED = 60
        VALIDATING_METADATA = 65
        REJECTED_BY_USER = 70
        METADATA_CONFIRMED = 75
        ACCEPTED_TO_PAS = 80
        IN_PACKAGING_SERVICE = 90
        PACKAGING_FAILED = 100
        SIP_IN_INGESTION = 110
        IN_PAS = 120
        REJECTED_FROM_PAS = 130
        IN_DISSEMINATION = 140

    preservation_state = models.IntegerField(
        choices=PreservationState.choices,
        default=PreservationState.NONE,
        help_text="Record state in PAS.",
    )

    def __str__(self):
        return str(self.id)
