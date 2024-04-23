import json
import uuid

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from simple_history.models import HistoricalRecords

from apps.common.models import AbstractBaseModel, AbstractDatasetProperty
from apps.core.models.concepts import Language

STORAGE_SERVICE_CHOICES = [(s, s) for s in settings.STORAGE_SERVICE_FILE_STORAGES]


class DataCatalog(AbstractBaseModel):
    """A curated collection of metadata about resources.

    RDF Class: dcat:Catalog

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog

    Attributes:
        title (HStoreField): catalog title
        dataset_versioning_enabled (models.BooleanField): does the catalog have versioning enabled
        harvested (models.BooleanField):
            are the catalog resources harvested from some other sources
        language (models.ManyToManyField): default language of the catalog
        publisher (models.ForeignKey): publisher of the cataloged resources
        access_rights (models.ForeignKey): default access rights for the cataloged resources
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
        blank=True,
    )
    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', blank=True, null=True
    )
    logo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    dataset_groups_create = models.ManyToManyField(
        Group,
        help_text="User groups that are allowed to create datasets in catalog.",
        related_name="catalogs_create_datasets",
        blank=True,
    )
    dataset_groups_admin = models.ManyToManyField(
        Group,
        help_text="User groups that are allowed to update all datasets in catalog.",
        related_name="catalogs_admin_datasets",
        blank=True,
    )
    allow_remote_resources = models.BooleanField(
        default=True, help_text="True when datasets in catalog can have remote resources."
    )
    storage_services = ArrayField(
        models.CharField(max_length=64, choices=STORAGE_SERVICE_CHOICES),
        default=list,
        blank=True,
        help_text="File storage services supported for datasets in catalog.",
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
