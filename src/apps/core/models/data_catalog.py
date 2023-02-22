import json
import uuid

from django.contrib.postgres.fields import HStoreField
from django.db import models
from simple_history.models import HistoricalRecords

from apps.common.models import (
    AbstractBaseModel,
    AbstractDatasetProperty,
    AbstractFreeformConcept,
)
from apps.core.models.concepts import AccessType, Language, License


class DataCatalog(AbstractBaseModel):
    """A curated collection of metadata about resources.

    RDF Class: dcat:Catalog

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog

    Attributes:
        title (HStoreField): catalog title
        dataset_versioning_enabled (models.BooleanField): does the catalog have versioning enabled
        harvested (models.BooleanField): are the catalog resources harvested from some other sources
        language (models.ManyToManyField): default language of the catalog
        publisher (models.ForeignKey): publisher of the cataloged resources
        access_rights (models.ForeignKey): default access rights for the cataloged resources
        dataset_schema (models.CharField): the schema which the catalog resources comply to
    """

    # https://www.w3.org/TR/vocab-dcat-3/#Property:resource_identifier
    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="A unique id of the resource being described or cataloged.",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    dataset_versioning_enabled = models.BooleanField(default=False)
    harvested = models.BooleanField(default=False)
    language = models.ManyToManyField(Language, related_name="catalogs")
    publisher = models.ForeignKey(
        "DatasetPublisher",
        on_delete=models.SET_NULL,
        related_name="catalogs",
        null=True,
    )
    access_rights = models.ForeignKey(
        "AccessRights", on_delete=models.SET_NULL, related_name="catalogs", null=True
    )

    class DatasetSchema(models.TextChoices):
        IDA = "ida"
        ATT = "att"
        DRF = "drf"

    DATASET_SCHEMA_CHOICES = (
        (DatasetSchema.IDA, "IDA Schema"),
        (DatasetSchema.ATT, "ATT Schema"),
        (DatasetSchema.DRF, "DRF Schema"),
    )

    dataset_schema = models.CharField(
        choices=DATASET_SCHEMA_CHOICES,
        default=DatasetSchema.IDA,
        max_length=6,
    )
    history = HistoricalRecords(m2m_fields=(language,))

    def __str__(self):
        return self.id


class CatalogHomePage(AbstractDatasetProperty):
    """A homepage of the catalog (a public Web document usually available in HTML).

    RDF Property: foaf:homepage

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:catalog_homepage

    Note:
        foaf:homepage is an inverse functional property (IFP) which means that it MUST be unique and precisely
        identify the Web-page for the resource. This property indicates the canonical Web-page, which might be helpful
        in cases where there is more than one Web-page about the resource.

    """

    history = HistoricalRecords()


class DatasetPublisher(AbstractBaseModel):
    """The entity responsible for making the item available.

    Note:
        Resources of type foaf:Agent are recommended as values for this property.

    RDF Property: dcterms:publisher

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_publisher

    Attributes:
        name (HStoreField): the name of the publisher organization
        homepage (models.ManyToManyField): webpage of the publisher
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = HStoreField(help_text='example: {"en": "name", "fi":"nimi"}')
    homepage = models.ManyToManyField(CatalogHomePage, related_name="publishers")
    history = HistoricalRecords(m2m_fields=(homepage,))

    def __str__(self):
        name = self.name
        if isinstance(name, str):
            name = json.loads(name)
        return str(next(iter(name.items())))


class AccessRights(AbstractBaseModel):
    """Information about who can access the resource or an indication of its security status.

    RFD Property: dcterms:accessRights

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_access_rights

    Attributes:
        license(models.ManyToManyField): ManyToMany relation to License
        access_type(AccessType): AccessType ForeignKey relation
        description(HStoreField): Description of the access rights
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ManyToManyField(
        License,
        related_name="access_rights",
    )
    access_type = models.ForeignKey(
        AccessType, on_delete=models.SET_NULL, related_name="access_rights", null=True
    )
    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', null=True, blank=True
    )
    history = HistoricalRecords(m2m_fields=(license,))

    class Meta:
        verbose_name_plural = "Access rights"

    def __str__(self):
        description = self.description
        if isinstance(description, str):
            description = json.loads(description)
        if description:
            return str(next(iter(description.items())))
        else:
            return self.access_type.pref_label.get("en", "access rights")


class AccessRightsRestrictionGrounds(AbstractFreeformConcept):
    """Justification for the restriction of a dataset.

    Attributes:
        access_rights(AccessRights): AccessRights ForeignKey relation
    """

    access_rights = models.ForeignKey(
        AccessRights, on_delete=models.CASCADE, related_name="restriction_grounds"
    )
