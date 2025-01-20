import json
import uuid
from typing import List

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.utils.translation import gettext as _
from simple_history.models import HistoricalRecords

from apps.common.models import AbstractBaseModel, AbstractDatasetProperty
from apps.core.models.concepts import Language
from apps.core.permissions import DataCatalogAccessPolicy
from apps.users.models import MetaxUser

STORAGE_SERVICE_CHOICES = [(s, s) for s in settings.STORAGE_SERVICE_FILE_STORAGES]


class PIDType(models.TextChoices):
    """All PID types."""

    URN = "URN", "URN"
    DOI = "DOI", "DOI"
    EXTERNAL = "external", "External"


class GeneratedPIDType(models.TextChoices):
    """PID types that are generated by Metax."""

    URN = "URN", "URN"
    DOI = "DOI", "DOI"


def default_allowed_pid_types() -> List[PIDType]:
    return [PIDType.EXTERNAL]


def default_publishing_channels() -> List["DataCatalog.PublishingChannel"]:
    return [DataCatalog.PublishingChannel.ETSIN, DataCatalog.PublishingChannel.TTV]


class DataCatalog(AbstractBaseModel):
    """A curated collection of metadata about resources.

    RDF Class: dcat:Catalog

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Catalog

    Attributes:
        title (HStoreField): catalog title
        dataset_versioning_enabled (models.BooleanField): does the catalog have versioning enabled
        is_external (models.BooleanField):
            are the catalog resources from some other sources
        language (models.ManyToManyField): default language of the catalog
        publisher (models.ForeignKey): publisher of the cataloged resources
    """

    # https://www.w3.org/TR/vocab-dcat-3/#Property:resource_identifier
    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="A unique id of the resource being described or cataloged.",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    dataset_versioning_enabled = models.BooleanField(default=False)
    is_external = models.BooleanField(default=False)
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
    rems_enabled = models.BooleanField(
        default=False, help_text="Is Resource Entitlement Management System enabled in catalog."
    )

    class PublishingChannel(models.TextChoices):
        ETSIN = "etsin", _("etsin")
        TTV = "ttv", _("ttv")

    publishing_channels = ArrayField(
        models.CharField(max_length=64, choices=PublishingChannel.choices),
        default=default_publishing_channels,
        blank=True,
        help_text="Channels in which datasets in this catalog will be published.",
    )
    allowed_pid_types = ArrayField(
        models.CharField(max_length=16, choices=PIDType.choices),
        default=default_allowed_pid_types,
        blank=True,
        help_text=(
            "Persistent identifier types supported for datasets in catalog. "
            "External PIDs are not managed by Metax."
        ),
    )
    history = HistoricalRecords(m2m_fields=(language,))

    def __str__(self):
        return self.id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._admin_user_cache = {}  # Map of user.id -> can admin datasets

    @property
    def managed_pid_types(self) -> list:
        """PID types that are allowed to be generated and managed by Metax."""
        return [v for v in self.allowed_pid_types if v != PIDType.EXTERNAL]

    @property
    def allow_external_pid(self) -> bool:
        return PIDType.EXTERNAL in self.allowed_pid_types

    @property
    def allow_generated_pid(self) -> bool:
        return any(self.managed_pid_types)

    def _can_admin_datasets(self, user: MetaxUser) -> bool:
        return DataCatalogAccessPolicy().query_object_permission(
            user=user, object=self, action="<op:admin_dataset>"
        )

    def can_admin_datasets(self, user: MetaxUser) -> bool:
        """Determine if user has permission to update all datasets in catalog.

        This is potentially called for every dataset in a list, so
        we memoize the value for the lifetime of the instance."""
        perms_cache = self._admin_user_cache
        if user.id not in perms_cache:
            perms_cache[user.id] = self._can_admin_datasets(user)
        return perms_cache[user.id]

    def can_create_datasets(self, user: MetaxUser) -> bool:
        """Determine if user has permission to create datasets in catalog."""
        return DataCatalogAccessPolicy().query_object_permission(
            user=user, object=self, action="<op:create_dataset>"
        )


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
