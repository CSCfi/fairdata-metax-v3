import logging
import uuid
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from simple_history.models import HistoricalRecords

from apps.actors.models import Actor, Organization
from apps.common.models import AbstractBaseModel
from apps.core.mixins import V2DatasetMixin
from apps.files.models import File, FileStorage
from apps.refdata import models as refdata

from .concepts import FieldOfScience, IdentifierType, Language, Theme
from .contract import Contract
from .data_catalog import AccessRights, DataCatalog
from .file_metadata import DatasetDirectoryMetadata, DatasetFileMetadata

logger = logging.getLogger(__name__)


class MetadataProvider(AbstractBaseModel):
    """Information about the creator of the metadata, and the associated organization.

    Attributes:
        user(django.contrib.auth.models.AbstractUser): User ForeignKey relation
        organization(models.CharField): Organization id
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.CharField(max_length=512)


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
        INITIALIZED = 0
        PROPOSED = 10
        TECHNICAL_METADATA_GENERATED = 20
        TECHNICAL_METADATA_GENERATED_FAILED = 30
        INVALID_METADATA = 40
        METADATA_VALIDATION_FAILED = 50
        VALIDATED_METADATA_UPDATED = 60
        VALIDATING_METADATA = 65
        VALID_METADATA = 70
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
        default=PreservationState.INITIALIZED,
        help_text="Record state in PAS.",
    )

    def __str__(self):
        return str(self.id)


class Dataset(V2DatasetMixin, CatalogRecord, AbstractBaseModel):
    """A collection of data available for access or download in one or many representations.

    RDF Class: dcat:Dataset

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Dataset

    Attributes:
        persistent_identifier (models.CharField): Resolvable persistent identifier
        issued (models.DateTimeField): Publication date of the dataset
        title (HStoreField): Title of the dataset
        description (HStoreField): Description of the dataset
        keyword (ArrayField): Dataset keywords
        language (models.ManyToManyField): Language ManyToMany relation
        theme (models.ManyToManyField): Keyword ManyToMany relation
        field_of_science (models.ManyToManyField): FieldOfScience ManyToMany relation
        access_rights (AccessRights): AccessRights ForeignKey relation
        is_deprecated (models.BooleanField): Is the dataset deprecated
        cumulation_started (models.DateTimeField): When cumulation has started
        cumulation_ended (models.DateTimeField): When cumulation has ended
        preservation_state (models.IntegerField): Number that represents long term preservation state of the dataset
        state (models.CharField): Is the dataset published or in draft state
        files (models.ManyToManyField): Files attached to dataset
        first (Self): First version of the dataset
        last (Self): Last version of the dataset
        previous (Self): Previous version of the dataset
        replaces (Self): Replaces this dataset
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
    language = models.ManyToManyField(
        Language,
        related_name="datasets",
        blank=True,
        limit_choices_to={"is_essential_choice": True},
    )
    theme = models.ManyToManyField(
        Theme,
        related_name="datasets",
        blank=True,
        limit_choices_to={"is_essential_choice": True},
    )
    field_of_science = models.ManyToManyField(
        FieldOfScience,
        related_name="datasets",
        blank=True,
        limit_choices_to={"is_essential_choice": True},
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
    last_cumulative_addition = models.DateTimeField(null=True, blank=True)

    class StateChoices(models.TextChoices):
        PUBLISHED = "published", _("Published")
        DRAFT = "draft", _("Draft")

    state = models.CharField(
        max_length=10,
        choices=StateChoices.choices,
        default=StateChoices.DRAFT,
    )

    files = models.ManyToManyField(File, related_name="datasets")

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

    class CumulativeState(models.IntegerChoices):
        NOT_CUMULATIVE = 0, _("Not cumulative")
        ACTIVE = 1, _("Active")
        CLOSED = 2, _("Closed")

    cumulative_state = models.IntegerField(
        choices=CumulativeState.choices,
        default=CumulativeState.NOT_CUMULATIVE,
        help_text="Cumulative state",
    )

    added_files_count: Optional[int] = None  # files added in request

    removed_files_count: Optional[int] = None  # files removed in request

    skip_files_m2m_changed = False  # enable to skip signal handler on file change

    @cached_property
    def total_files_aggregates(self) -> dict:
        return self.files.aggregate(
            total_files_count=Count("*"), total_files_byte_size=Coalesce(Sum("byte_size"), 0)
        )

    @property
    def total_files_byte_size(self) -> int:
        return self.total_files_aggregates["total_files_byte_size"]

    @property
    def total_files_count(self) -> int:
        return self.total_files_aggregates["total_files_count"]

    @cached_property
    def file_storage(self) -> Optional[FileStorage]:
        """FileStorage is not currently stored in model and has to be determined from files."""
        if file := self.dataset.files.only("file_storage").select_related("file_storage").first():
            return file.file_storage

    @property
    def project_identifier(self) -> Optional[str]:
        if storage := self.file_storage:
            return storage.project_identifier

    @property
    def storage_service(self) -> Optional[str]:
        if storage := self.file_storage:
            return storage.storage_service

    def clear_cached_file_properties(self):
        """Clear cached file properties after changes to dataset files."""
        for prop in ["total_files_aggregates", "file_storage"]:
            try:
                delattr(self, prop)
            except AttributeError:
                logger.info(f"No property {prop} in cache.")

    def remove_unused_file_metadata(self):
        """Remove file and directory metadata for files and directories not in dataset."""

        # remove metadata for files not in dataset
        unused_file_metadata = DatasetFileMetadata.objects.filter(dataset=self).exclude(
            file__datasets=self
        )
        unused_file_metadata.delete()

        # remove metadata for directories not in dataset
        file_storages = FileStorage.objects.filter(
            datasetdirectorymetadata__in=self.directory_metadata.all()
        )
        # only one storage project is expected but this works with multiple
        for file_storage in file_storages:
            dataset_directory_paths = file_storage.get_directory_paths(dataset=self)
            unused_directory_metadata = DatasetDirectoryMetadata.objects.filter(
                file_storage=file_storage
            ).exclude(directory_path__in=dataset_directory_paths)
            unused_directory_metadata.delete()

    def delete(self, *args, **kwargs):
        if self.access_rights:
            self.access_rights.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)


class DatasetActor(Actor):
    """Actors associated with a Dataset.

    Attributes:
        dataset (Dataset): Dataset ForeignKey relation
        role (models.CharField): Role of the actor
    """

    @classmethod
    def get_instance_from_v2_dictionary(cls, obj: Dict, dataset: Dataset, role: str):
        """

        Args:
            obj (Dict): v2 actor dictionary
            dataset (Dataset): Dataset where the actor will be present
            role (str): Role of the actor in the dataset

        Returns:
            DatasetActor: get or created DatasetActor instance

        """
        actor_type = obj["@type"]
        organization: Organization = None
        user = None
        if actor_type == "Organization":
            organization = Organization.get_instance_from_v2_dictionary(obj)
        elif actor_type == "Person":
            name = obj.get("name")
            user, created = get_user_model().objects.get_or_create(
                username=name, defaults={"username": name}
            )
            if member_of := obj.get("member_of"):
                organization = Organization.get_instance_from_v2_dictionary(member_of)

        dataset_actor, created = cls.objects.get_or_create(
            dataset=dataset, user=user, organization=organization, role=role
        )
        return dataset_actor

    dataset = models.ForeignKey(Dataset, related_name="actors", on_delete=models.CASCADE)

    class RoleChoices(models.TextChoices):
        CREATOR = "creator", _("Creator")
        CONTRIBUTOR = "contributor", _("Contributor")
        PUBLISHER = "publisher", _("Publisher")
        CURATOR = "curator", _("Curator")
        RIGHTS_HOLDER = "rights_holder", _("Rights holder")
        PROVENANCE = "provenance", _("Provenance")

    role = models.CharField(
        max_length=100, choices=RoleChoices.choices, default=RoleChoices.CREATOR
    )


class Temporal(AbstractBaseModel):
    """Time period that is covered by the dataset, i.e. period of observations.

    Attributes:
        start_date (models.DateTimeField): Start of the pediod
        end_date (models.DateTimeField): End of the period
        dataset (Dataset): Dataset ForeignKey relation
        provenance (Provenance): Provenance ForeignKey relation, if part of Provenance
    """

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    dataset = models.ForeignKey(
        "Dataset",
        on_delete=models.CASCADE,
        related_name="temporal",
        null=True,
        blank=True,
    )
    provenance = models.OneToOneField(
        "Provenance",
        on_delete=models.CASCADE,
        related_name="temporal",
        null=True,
        blank=True,
    )


class OtherIdentifier(AbstractBaseModel):
    """Other identifier that dataset has in other services.

    Attributes:
        notation(models.CharField): Identifier
        identifier_type(IdentifierType): IdentifierType ForeignKey relation
        dataset(Dataset): Dataset ForeignKey relation
    """
    # ArrayField for as_wkt objects
    # ForeignKey to Location
    notation = models.CharField(max_length=512)
    identifier_type = models.ForeignKey(
        IdentifierType, on_delete=models.CASCADE, related_name="dataset_identifiers"
    )
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="other_identifiers"
    )


class DatasetProject(AbstractBaseModel):
    """Funding project for the dataset

    Attributes:
        dataset(models.ManyToManyField): ManyToMany relation to Dataset
        project_identifier(models.CharField): Project identifier
        funding_agency(models.ManyToManyField): The Organization funding the project
        funder_identifier(models.CharField): Unique identifier for the project that is being used by the project funder
        participating_organization(models.ManyToManyField): The Organization participating in the project
        name(HStoreField): Name of the project
        funder_type(refdata.FunderType): FunderType ForeignKey relation
    """

    dataset = models.ManyToManyField(Dataset, related_name="is_output_of")
    project_identifier = models.CharField(max_length=512, blank=True, null=True)
    funding_agency = models.ManyToManyField(Organization, related_name="is_funding")
    participating_organization = models.ManyToManyField(
        Organization, related_name="participating_in"
    )
    funder_identifier = models.CharField(max_length=512, blank=True, null=True)
    name = HStoreField(blank=True, null=True)
    funder_type = models.ForeignKey(
        refdata.FunderType, on_delete=models.SET_NULL, null=True, blank=True
    )
