import json
import uuid
from django.conf import settings
from .abstracts import AbstractBaseModel, AbstractDatasetProperty
from django.contrib.postgres.fields import HStoreField
from django.db import models


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
        research_dataset_schema (models.CharField): the schema which the catalog resources comply to

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
    language = models.ManyToManyField("DatasetLanguage", related_name="catalogs")
    publisher = models.ForeignKey(
        "DatasetPublisher",
        on_delete=models.SET_NULL,
        related_name="catalogs",
        null=True,
    )
    access_rights = models.ForeignKey(
        "AccessRight", on_delete=models.SET_NULL, related_name="catalogs", null=True
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

    research_dataset_schema = models.CharField(
        choices=DATASET_SCHEMA_CHOICES,
        default=DatasetSchema.IDA,
        max_length=6,
    )

    def __str__(self):
        return self.id


class DatasetLanguage(AbstractDatasetProperty):
    """A language of the item.

    This refers to the natural language used for textual metadata (i.e. titles, descriptions, etc)
    of a cataloged resource (i.e. dataset or service) or the textual values of a dataset distribution

    Note:
        Repeat this property if the resource is available in multiple languages.

    Note:
        The value(s) provided for members of a catalog (i.e. dataset or service)
        override the value(s) provided for the catalog if they conflict.

    Note:
        If representations of a dataset are available for each language separately,
        define an instance of dcat:Distribution for each language and describe the specific language of each
        distribution using dcterms:language (i.e. the dataset will have multiple dcterms:language values and
        each distribution will have just one as the value of its dcterms:language property).

    DRF Property: dcterms:language

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_language
    """


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

    def __str__(self):
        name = self.name
        if isinstance(name, str):
            name = json.loads(name)
        return str(next(iter(name.items())))


class DatasetLicense(AbstractDatasetProperty):
    """A legal document under which the resource is made available.

    RFD Property: dcterms:license

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_license
    """


class AccessType(AbstractDatasetProperty):
    """Accessibility of the resource"""


class AccessRight(AbstractBaseModel):
    """Information about who can access the resource or an indication of its security status.

    RFD Property: dcterms:accessRights

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_access_rights

    Attributes:
        license (models.ForeignKey): Resource license
        access_type (models.ForeignKey): Resource Access Type
        description (HStoreField): description of the access rights
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(
        DatasetLicense,
        on_delete=models.SET_NULL,
        related_name="access_rights",
        null=True,
    )
    access_type = models.ForeignKey(
        AccessType, on_delete=models.SET_NULL, related_name="access_rights", null=True
    )
    description = HStoreField(help_text='example: {"en":"description", "fi":"kuvaus"}')

    def __str__(self):
        description = self.description
        if isinstance(description, str):
            description = json.loads(description)
        return str(next(iter(description.items())))
