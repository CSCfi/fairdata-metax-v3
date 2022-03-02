from django.contrib.postgres.fields import HStoreField, ArrayField
from django.db import models

# Create your models here.
from django.db import models

# Create your models here.
from model_utils.models import TimeStampedModel, SoftDeletableModel


class AbstractBaseModel(TimeStampedModel, SoftDeletableModel):
    """Adds soft-delete and created / modified timestamp functionalities

    Added fields are:
     - created
     - modified
     - is_removed
    """

    class Meta:
        abstract = True
        get_latest_by = "modified"
        ordering = ["created"]


class AbstractDatasetProperty(AbstractBaseModel):
    """Base class for simple refdata fields with only identifier and title properties

    """
    identifier = models.URLField(max_length=512, primary_key=True)
    title = HStoreField()

    def __str__(self):
        return self.identifier

    class Meta:
        abstract = True


class DatasetLanguage(AbstractDatasetProperty):
    """A language of the item.

    This refers to the natural language used for textual metadata (i.e. titles, descriptions, etc)
    of a cataloged resource (i.e. dataset or service) or the textual values of a dataset distribution

    Note: Repeat this property if the resource is available in multiple languages.

    Note: The value(s) provided for members of a catalog (i.e. dataset or service)
    override the value(s) provided for the catalog if they conflict.

    Note: If representations of a dataset are available for each language separately,
    define an instance of dcat:Distribution for each language and describe the specific language of each
    distribution using dcterms:language (i.e. the dataset will have multiple dcterms:language values and
    each distribution will have just one as the value of its dcterms:language property).

    DRF Property: dcterms:language

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_language
    """


class CatalogHomePage(AbstractDatasetProperty):
    """A homepage of the catalog (a public Web document usually available in HTML).

    Note: foaf:homepage is an inverse functional property (IFP) which means that it MUST be unique and precisely
    identify the Web-page for the resource. This property indicates the canonical Web-page,
    which might be helpful in cases where there is more than one Web-page about the resource.

    RDF Property: foaf:homepage

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:catalog_homepage
    """


class DatasetPublisher(AbstractBaseModel):
    """The entity responsible for making the item available.

    Note: Resources of type foaf:Agent are recommended as values for this property.

    RDF Property: dcterms:publisher

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_publisher
    """

    name = HStoreField()
    homepage = models.ManyToManyField(CatalogHomePage, related_name="publishers")

    def __str__(self):
        return str(next(iter(self.name.items())))


class DatasetLicense(AbstractDatasetProperty):
    """A legal document under which the resource is made available.

    RFD Property: dcterms:license

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_license
    """

    license = models.URLField(max_length=512)


class AccessType(AbstractDatasetProperty):
    """Accessibility of the resource"""


class AccessRight(AbstractBaseModel):
    """Information about who can access the resource or an indication of its security status.

    RFD Property: dcterms:accessRights

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_access_rights
    """

    license = models.ForeignKey(
        DatasetLicense,
        on_delete=models.SET_NULL,
        related_name="access_rights",
        null=True,
    )
    access_type = models.ForeignKey(
        AccessType, on_delete=models.SET_NULL, related_name="access_rights", null=True
    )
    description = HStoreField()

    def __str__(self):
        return str(next(iter(self.description.items())))


class DataCatalog(AbstractBaseModel):
    """A curated collection of metadata about resources.

    RDF Class: dcat:Catalog

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog
    """

    # https://www.w3.org/TR/vocab-dcat-3/#Property:resource_identifier
    identifier = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="A unique identifier of the resource being described or cataloged.",
    )

    dataset_versioning_enabled = models.BooleanField(default=False)
    harvested = models.BooleanField(default=False)
    title = HStoreField()
    language = models.ManyToManyField(DatasetLanguage, related_name="catalogs")
    publisher = models.ForeignKey(
        DatasetPublisher, on_delete=models.SET_NULL, related_name="catalogs", null=True
    )
    access_rights = models.ForeignKey(
        AccessRight, on_delete=models.SET_NULL, related_name="catalogs", null=True
    )

    class DatasetSchemaChoices(models.TextChoices):
        SCHEMA_IDA = "ida"
        SCHEMA_ATT = "att"
        SCHEMA_DRF = "drf"

    DATASET_SCHEMA_CHOICES = (
        (DatasetSchemaChoices.SCHEMA_IDA, "IDA Schema"),
        (DatasetSchemaChoices.SCHEMA_ATT, "ATT Schema"),
        (DatasetSchemaChoices.SCHEMA_DRF, "DRF Schema"),
    )

    research_dataset_schema = models.CharField(
        choices=DATASET_SCHEMA_CHOICES,
        default=DatasetSchemaChoices.SCHEMA_IDA,
        max_length=6,
    )

    def __str__(self):
        return self.identifier
