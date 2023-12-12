import logging
import uuid
from typing import Dict, Optional, Tuple

from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from typing_extensions import Self

from apps.actors.models import Actor, Organization, Person
from apps.common.helpers import ensure_instance_id, prepare_for_copy
from apps.common.mixins import CopyableModelMixin
from apps.common.models import AbstractBaseModel, MediaTypeValidator
from apps.core.models.concepts import FileType, RelationType, UseCategory
from apps.core.models.file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata
from apps.files.models import File, FileStorage
from apps.refdata import models as refdata

from .dataset import Dataset

logger = logging.getLogger(__name__)


class DatasetActor(CopyableModelMixin, Actor):
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

    roles = ArrayField(
        models.CharField(choices=RoleChoices.choices, default=RoleChoices.CREATOR, max_length=30),
        default=list,
        blank=True,
    )
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="actors", null=True, blank=True
    )

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
        dataset (Dataset): Dataset ForeignKey relation
        end_date (models.DateTimeField): End of the period
        provenance (Provenance): Provenance ForeignKey relation, if part of Provenance
        start_date (models.DateTimeField): Start of the pediod
    """

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
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
        funder_identifier(models.CharField): Unique identifier for the project
            that is being used by the project funder
        funder_type(refdata.FunderType): FunderType ForeignKey relation
        funding_agency(models.ManyToManyField): The Organization funding the project
        name(HStoreField): Name of the project
        participating_organization(models.ManyToManyField):
            The Organization participating in the project
        project_identifier(models.CharField): Project identifier
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
    """Collection of files associated with a Dataset

    Attributes:
        dataset(models.OneToOneField): Dataset associated with the fileset
        files(models.ManyToManyField): Files associated with the fileset
        storage(models.ForeignKey): FileStorage of the fileset

    """

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
    def csc_project(self) -> str:
        return self.storage.csc_project

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
        actor: ForeignKey relation to Actor
        contribution_type: ForeignKey relation to ContributorType
        participating_organization: ForeignKey relation to Organization
        project: ForeignKey relation to DatasetProject

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
    """
    Attributes:
        access_url(models.URLField): The URL where the resource can be accessed.
        checksum(models.TextField): The checksum of the resource
        dataset(Dataset): Dataset associated with remote resource
        description(HStoreField): Resource description
        download_url(models.URLField): The URL where the resource can be downloaded
        file_type(FileType): The file type of the resource
        mediatype(models.TextField): The mediatype of the resource
        title(HStoreField): Resource title
        use_category(models.ForeignKey): Category of the resource
    """

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


class EntityRelation(AbstractBaseModel):
    """An entity related to the dataset.

    RDF Class: dcterms:relation

    Source: [DCAT Version 3](https://www.w3.org/TR/vocab-dcat-3/#Property:resource_relation)
    """

    entity = models.ForeignKey(
        "Entity",
        on_delete=models.CASCADE,
        related_name="relation",
    )
    relation_type = models.ForeignKey(RelationType, on_delete=models.CASCADE)
    dataset = models.ForeignKey(
        "Dataset",
        on_delete=models.CASCADE,
        related_name="relation",
        null=True,
        blank=True,
    )
