import logging
import uuid
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from model_utils import FieldTracker
from rest_framework.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from typing_extensions import Self

from apps.actors.models import Actor, Organization, Person
from apps.common.models import AbstractBaseModel, MediaTypeValidator
from apps.core.mixins import V2DatasetMixin
from apps.core.models.concepts import UseCategory
from apps.files.models import File, FileStorage
from apps.refdata import models as refdata
from apps.common.helpers import prepare_for_copy, ensure_instance_id
from apps.common.mixins import CopyableModelMixin


from .concepts import FieldOfScience, FileType, IdentifierType, Language, ResearchInfra, Theme
from .contract import Contract
from .data_catalog import AccessRights, DataCatalog
from .file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata
from simple_history.utils import update_change_reason


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
        notation(models.CharField): Identifier
        identifier_type(IdentifierType): IdentifierType ForeignKey relation
        dataset(Dataset): Dataset ForeignKey relation
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


class Dataset(V2DatasetMixin, CopyableModelMixin, CatalogRecord, AbstractBaseModel):
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
        preservation_state (models.IntegerField): Number that represents
            long term preservation state of the dataset
        state (models.CharField): Is the dataset published or in draft state
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
    infrastructure = models.ManyToManyField(
        ResearchInfra,
        related_name="datasets",
        blank=True,
    )
    access_rights = models.ForeignKey(
        AccessRights,
        on_delete=models.SET_NULL,
        related_name="datasets",
        null=True,
    )
    other_identifiers = models.ManyToManyField(
        OtherIdentifier,
        blank=True,
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
    # First, last replaces, next

    other_versions = models.ManyToManyField("self", db_index=True)
    history = HistoricalRecords(
        m2m_fields=(language, theme, field_of_science, infrastructure, other_identifiers)
    )

    class CumulativeState(models.IntegerChoices):
        NOT_CUMULATIVE = 0, _("Not cumulative")
        ACTIVE = 1, _("Active")
        CLOSED = 2, _("Closed")

    cumulative_state = models.IntegerField(
        choices=CumulativeState.choices,
        default=CumulativeState.NOT_CUMULATIVE,
        help_text="Cumulative state",
    )

    published_revision = models.IntegerField(default=0, blank=True, editable=False)
    draft_revision = models.IntegerField(default=0, blank=True, editable=False)
    tracker = FieldTracker(
        fields=["state", "published_revision", "cumulative_state", "draft_revision"]
    )

    @cached_property
    def latest_published_revision(self):
        return self.get_published_revision(self.published_revision)

    @cached_property
    def first_published_revision(self):
        return self.get_published_revision(1)

    @cached_property
    def first_version(self):
        return self.other_versions.first()

    @cached_property
    def last_version(self):
        return self.other_versions.last()

    @cached_property
    def next_version(self):
        return self.other_versions.filter(created__gt=self.created).first()

    @cached_property
    def previous_version(self):
        return self.other_versions.filter(created__lt=self.created).last()

    def get_published_revision(self, version: int):
        revision = self.history.filter(history_change_reason=f"published-{version}").first()
        if revision:
            return revision.instance

    def all_published_revisions(self):
        revisions = self.history.filter(history_change_reason__contains="published-")
        return [revision.instance for revision in revisions if revision.instance]

    @classmethod
    def create_copy(cls, original: "Dataset") -> Tuple[Self, Self]:
        copy_languages = original.language.all()
        copy_themes = original.theme.all()
        copy_field_of_sciences = original.field_of_science.all()

        copy = prepare_for_copy(original)
        if original.access_rights:
            copy.access_rights, _ = AccessRights.create_copy(original.access_rights)

        new_actors = []
        # reverse foreign keys
        for actor in original.actors.all():
            new_actor, _ = DatasetActor.create_copy(actor, copy)
            new_actors.append(new_actor)

        new_provs = []
        for prov in original.provenance.all():
            from apps.core.models import Provenance

            new_prov, _ = Provenance.create_copy(prov, copy)
            new_provs.append(new_prov)

        # Custom field values
        copy.persistent_identifier = None
        copy.catalogrecord_ptr = None
        copy.state = cls.StateChoices.DRAFT
        copy.published_revision = 0
        copy.created = timezone.now()
        copy.modified = timezone.now()
        copy.save()

        # reverse set
        copy.actors.set(new_actors)
        copy.provenance.set(new_provs)

        # Many to Many
        copy.language.set(copy_languages)
        copy.theme.set(copy_themes)
        copy.field_of_science.set(copy_field_of_sciences)

        copy.other_versions.add(original)
        for version in original.other_versions.exclude(id=copy.id):
            copy.other_versions.add(version)

        return copy, original

    def delete(self, *args, **kwargs):
        if self.access_rights:
            self.access_rights.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)

    def _deny_if_trying_to_change_to_cumulative(self):
        cumulative_changed, previous_cumulative = self.tracker.has_changed(
            "cumulative_state"
        ), self.tracker.previous("cumulative_state")
        if (
            cumulative_changed
            and previous_cumulative == self.CumulativeState.NOT_CUMULATIVE
            and self.cumulative_state != self.CumulativeState.NOT_CUMULATIVE
            and self.first_published_revision is not None
        ):
            raise ValidationError("Cannot change cumulative state from NOT_CUMULATIVE to ACTIVE")
        else:
            return False

    def _should_increase_published_revision(self):
        state_has_changed, previous_state = self.tracker.has_changed(
            "state"
        ), self.tracker.previous("state")
        if (
            state_has_changed
            and previous_state == self.StateChoices.DRAFT
            or previous_state == self.StateChoices.PUBLISHED
            and self.state != self.StateChoices.DRAFT
            or self.state == self.StateChoices.PUBLISHED
            and self.published_revision == 0
        ):
            return True
        else:
            return False

    def _should_increase_draft_revision(self):
        state_has_changed, previous_state = self.tracker.has_changed(
            "state"
        ), self.tracker.previous("state")
        if (
            state_has_changed
            and previous_state == self.StateChoices.DRAFT
            and self.state == self.StateChoices.DRAFT
            or previous_state == self.StateChoices.PUBLISHED
            and self.state == self.StateChoices.DRAFT
        ):
            return True
        else:
            return False

    def _should_use_versioning(self):
        from apps.core.models import LegacyDataset

        if isinstance(self, LegacyDataset):
            return False
        elif self.data_catalog and self.data_catalog.dataset_versioning_enabled:
            return True
        return False

    def change_update_reason(self, reason: str):
        from apps.core.models import LegacyDataset

        if not isinstance(self, LegacyDataset):
            update_change_reason(self, reason)

    def publish(self):
        if not self.persistent_identifier:
            raise ValidationError("Dataset has to have persistent identifier when publishing")
        self.published_revision += 1
        self.draft_revision = 0
        if not self.issued:
            self.issued = timezone.now()

    def save(self, *args, **kwargs):
        if self._should_use_versioning():
            self._deny_if_trying_to_change_to_cumulative()

            if self._should_increase_published_revision():
                self.publish()
            if self._should_increase_draft_revision():
                self.draft_revision += 1
            published_version_changed = self.tracker.has_changed("published_revision")
            draft_version_changed = self.tracker.has_changed("draft_revision")
            super().save(*args, **kwargs)
            if published_version_changed:
                self.change_update_reason(f"{self.state}-{self.published_revision}")
            elif draft_version_changed:
                self.change_update_reason(
                    f"{self.state}-{self.published_revision}.{self.draft_revision}"
                )
        else:
            self.skip_history_when_saving = True
            if self.state == self.StateChoices.PUBLISHED and self.published_revision == 0:
                self.published_revision = 1
            super().save(*args, **kwargs)


class DatasetActor(Actor, CopyableModelMixin):
    """Actors associated with a Dataset.

    Attributes:
        dataset (Dataset): Dataset ForeignKey relation
        role (models.CharField): Role of the actor
    """

    class RoleChoices(models.TextChoices):
        CREATOR = "creator", _("Creator")
        CONTRIBUTOR = "contributor", _("Contributor")
        PUBLISHER = "publisher", _("Publisher")
        CURATOR = "curator", _("Curator")
        RIGHTS_HOLDER = "rights_holder", _("Rights holder")
        PROVENANCE = "provenance", _("Provenance")

    roles = ArrayField(
        models.CharField(choices=RoleChoices.choices, default=RoleChoices.CREATOR, max_length=30),
        null=True,
    )
    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE, related_name="actors")

    @classmethod
    def create_copy(cls, original: Self, dataset=None) -> Tuple[Self, Self]:
        person = original.person
        copy = prepare_for_copy(original)
        if person:
            person_copy, _ = Person.create_copy(person)
            copy.person = person_copy
        if dataset:
            ensure_instance_id(dataset)
            copy.dataset = dataset
        copy.save()
        return copy, original

    def add_role(self, role: str) -> bool:
        """Adds a roles to the actor.

        Args:
            role (str): The roles to add to the actor.

        Returns:
            bool: A boolean indicating whether the roles was added or not.

        Raises:
            ValueError: If the roles is not valid.
        """

        if self.roles is None:
            self.roles = [role]
            return True
        else:
            if role not in self.roles:
                self.roles.append(role)
                return True
        return False

    @classmethod
    def get_instance_from_v2_dictionary(
        cls, obj: Dict, dataset: "Dataset", role: str
    ) -> Tuple["DatasetActor", bool]:
        """

        Args:
            obj (Dict): v2 actor dictionary
            dataset (Dataset): Dataset where the actor will be present
            role (str): Role of the actor in the dataset

        Returns:
            DatasetActor: get or created DatasetActor instance

        """
        actor_type = obj["@type"]
        organization: Optional[Organization] = None
        person: Optional[Person] = None
        if actor_type == "Organization":
            organization = Organization.get_instance_from_v2_dictionary(obj)
        elif actor_type == "Person":
            name = obj.get("name")
            person = Person(name=name)
            person.save()
            if member_of := obj.get("member_of"):
                organization = Organization.get_instance_from_v2_dictionary(member_of)
        actor, created = cls.objects.get_or_create(
            organization=organization, person=person, dataset=dataset
        )
        if not actor.roles:
            actor.roles = [role]
        elif role not in actor.roles:
            actor.roles.append(role)
        actor.save()
        return actor, created


class Temporal(AbstractBaseModel):
    """Time period that is covered by the dataset, i.e. period of observations.

    Attributes:
        start_date (models.DateTimeField): Start of the pediod
        end_date (models.DateTimeField): End of the period
        dataset (Dataset): Dataset ForeignKey relation
        provenance (Provenance): Provenance ForeignKey relation, if part of Provenance
    """

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
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


class DatasetProject(AbstractBaseModel):
    """Funding project for the dataset

    Attributes:
        dataset(models.ManyToManyField): ManyToMany relation to Dataset
        project(models.CharField): Project identifier
        funding_agency(models.ManyToManyField): The Organization funding the project
        funder_identifier(models.CharField): Unique identifier for the project
            that is being used by the project funder
        participating_organization(models.ManyToManyField): The Organization
            participating in the project
        name(HStoreField): Name of the project
        funder_type(refdata.FunderType): FunderType ForeignKey relation
    """

    dataset = models.ManyToManyField(Dataset, related_name="is_output_of")
    project_identifier = models.CharField(max_length=512, blank=True, null=True)
    funding_agency = models.ManyToManyField("ProjectContributor", related_name="is_funding")
    funder_identifier = models.CharField(max_length=512, blank=True, null=True)
    participating_organization = models.ManyToManyField(
        "ProjectContributor", related_name="is_participating"
    )
    name = HStoreField(blank=True, null=True)
    funder_type = models.ForeignKey(
        refdata.FunderType, on_delete=models.SET_NULL, null=True, blank=True
    )


class FileSet(AbstractBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage = models.ForeignKey(FileStorage, related_name="file_sets", on_delete=models.CASCADE)
    dataset = models.OneToOneField(Dataset, related_name="file_set", on_delete=models.CASCADE)
    files = models.ManyToManyField(File, related_name="file_sets")

    added_files_count: Optional[int] = None  # files added in request

    removed_files_count: Optional[int] = None  # files removed in request

    skip_files_m2m_changed = False  # enable to skip signal handler on file changes

    @cached_property
    def total_files_aggregates(self) -> dict:
        return self.files.aggregate(
            total_files_count=Count("*"), total_files_size=Coalesce(Sum("size"), 0)
        )

    @property
    def total_files_size(self) -> int:
        return self.total_files_aggregates["total_files_size"]

    @property
    def total_files_count(self) -> int:
        return self.total_files_aggregates["total_files_count"]

    @property
    def project(self) -> str:
        return self.storage.project

    @property
    def storage_service(self) -> str:
        return self.storage.storage_service

    def clear_cached_file_properties(self):
        """Clear cached file properties after changes to FileSet files."""
        for prop in ["total_files_aggregates"]:
            try:
                delattr(self, prop)
            except AttributeError:
                logger.info(f"No property {prop} in cache.")

    def remove_unused_file_metadata(self):
        """Remove file and directory metadata for files and directories not in FileSet."""

        # remove metadata for files not in FileSet
        unused_file_metadata = FileSetFileMetadata.objects.filter(file_set=self).exclude(
            file__file_sets=self
        )
        unused_file_metadata.delete()

        # remove metadata for directories not in FileSet
        storages = FileStorage.objects.filter(
            filesetdirectorymetadata__in=self.directory_metadata.all()
        )
        # only one storage project is expected but this works with multiple
        for storage in storages:
            dataset_pathnames = storage.get_directory_paths(file_set=self)
            unused_directory_metadata = FileSetDirectoryMetadata.objects.filter(
                storage=storage
            ).exclude(pathname__in=dataset_pathnames)
            unused_directory_metadata.delete()


class ProjectContributor(AbstractBaseModel):
    """Project contributing organizations

    Attributes:
        participating_organization: ForeignKey relation to Organization
        contribution_type: ForeignKey relation to ContributorType
        project: ForeignKey relation to DatasetProject
        actor: ForeignKey relation to Actor

    """

    participating_organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="contributions"
    )

    contribution_type = models.ManyToManyField(
        refdata.ContributorType,
        related_name="projects",
    )
    project = models.ForeignKey(
        DatasetProject, on_delete=models.CASCADE, related_name="contributors"
    )
    actor = models.ForeignKey(
        Actor, on_delete=models.CASCADE, related_name="actor_project", null=True, blank=True
    )

    def __str__(self):
        return str(self.participating_organization.pref_label["fi"])


class RemoteResource(AbstractBaseModel):
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="remote_resources"
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', blank=True, null=True
    )
    access_url = models.URLField(max_length=2048, blank=True, null=True)
    download_url = models.URLField(max_length=2048, blank=True, null=True)
    checksum = models.TextField(blank=True, null=True)
    mediatype = models.TextField(
        help_text=_('IANA media type as a string, e.g. "text/csv".'),
        validators=[MediaTypeValidator()],
        blank=True,
        null=True,
    )
    use_category = models.ForeignKey(UseCategory, on_delete=models.CASCADE)
    file_type = models.ForeignKey(FileType, on_delete=models.CASCADE, blank=True, null=True)
