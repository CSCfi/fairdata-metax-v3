import logging
import uuid
from typing import Dict, Optional, Tuple

from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from apps.actors.models import Actor, Organization, Person
from apps.common.copier import ModelCopier
from apps.common.models import AbstractBaseModel, MediaTypeValidator
from apps.core.models.concepts import FileType, RelationType, UseCategory
from apps.core.models.file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata
from apps.files.models import File, FileStorage
from apps.refdata import models as refdata

from .dataset import Dataset

logger = logging.getLogger(__name__)


class DatasetActor(Actor):
    """Actors associated with a Dataset.

    Attributes:
        dataset (Dataset): Dataset ForeignKey relation
        role (models.CharField): Role of the actor
    """

    copier = ModelCopier(
        copied_relations=["person", "organization"], parent_relations=["dataset", "provenance"]
    )

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
    actors_order = models.IntegerField(default=0, help_text=_("Position in dataset actors list."))

    class Meta:
        ordering = ["actors_order", "created"]

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

    def get_email(self) -> Optional[str]:
        """Return email of actor if any."""
        if self.person and self.person.email:
            return self.person.email
        else:
            org = self.organization
            while org:
                if org.email:
                    return org.email
                org = org.parent
        return None

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
            organization = Organization.get_instance_from_v2_dictionary(obj, dataset)
            actor, created = cls.objects.get_or_create(
                organization=organization, person__isnull=True, dataset=dataset
            )
        else:
            name = obj.get("name")
            person = Person(name=name)
            person.save()
            dataset.created_objects.update(["Person"])
            if member_of := obj.get("member_of"):
                organization = Organization.get_instance_from_v2_dictionary(member_of, dataset)
            actor, created = cls.objects.get_or_create(
                organization=organization, dataset=dataset, person=person
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

    copier = ModelCopier(copied_relations=[], parent_relations=["dataset", "provenance"])

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
        title(HStoreField): Name of the project
        project_identifier(models.CharField): Project's external identifier
        participating_organizations(models.ManyToManyField): Project's participating organizations
        funders(models.ManyToManyField): Funding agencies of the project
    """

    copier = ModelCopier(
        copied_relations=["funding", "participating_organizations"], parent_relations=["dataset"]
    )

    dataset = models.ForeignKey(
        "Dataset", related_name="projects", on_delete=models.CASCADE, null=True, blank=True
    )
    title = HStoreField(blank=True, null=True)
    project_identifier = models.CharField(max_length=512, blank=True, null=True)
    participating_organizations = models.ManyToManyField(Organization, related_name="projects")
    funding = models.ManyToManyField("Funding", related_name="projects")


class Funding(AbstractBaseModel):
    """Funding for the project and dataset

    Attributes:
        agency(models.ForeignKey): Agency that Funds the project
        funding_identifier(models.CharField): Funding identifier that is
            given by the funder organization
    """

    copier = ModelCopier(copied_relations=["funder"], parent_relations=[])

    funder = models.ForeignKey("Funder", related_name="funding", on_delete=models.CASCADE)
    funding_identifier = models.CharField(max_length=255, blank=True, null=True)


class Funder(AbstractBaseModel):
    """Project's Funder Agency

    Attributes:
    organization(models.ForeignKey): Organization that granted the funds
    funder_type(models.ForeignKey): Funder type reference
    """

    copier = ModelCopier(copied_relations=["organization"], parent_relations=[])

    organization = models.ForeignKey(
        Organization, related_name="agencies", on_delete=models.SET_NULL, null=True, blank=True
    )
    funder_type = models.ForeignKey(
        refdata.FunderType, blank=True, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.pref_label['fi']}"


class FileSet(AbstractBaseModel):
    """Collection of files associated with a Dataset

    Attributes:
        dataset(models.OneToOneField): Dataset associated with the fileset
        files(models.ManyToManyField): Files associated with the fileset
        storage(models.ForeignKey): FileStorage of the fileset

    """

    copier = ModelCopier(
        copied_relations=["file_metadata", "directory_metadata"], parent_relations=["dataset"]
    )

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

    copier = ModelCopier(copied_relations=[], parent_relations=["dataset"])

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

    copier = ModelCopier(copied_relations=["entity"], parent_relations=["dataset"])

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
