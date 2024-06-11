import logging

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.signals import post_delete
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from model_utils import FieldTracker
from rest_framework.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from typing_extensions import Self

from apps.common.copier import ModelCopier
from apps.common.exceptions import TopLevelValidationError
from apps.common.helpers import datetime_to_date
from apps.common.history import SnapshotHistoricalRecords
from apps.common.models import AbstractBaseModel
from apps.core.models.access_rights import AccessRights, AccessTypeChoices
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.models.data_catalog import DataCatalog
from apps.core.models.mixins import V2DatasetMixin
from apps.core.permissions import DataCatalogAccessPolicy
from apps.core.services.pid_ms_client import PIDMSClient, ServiceUnavailableError
from apps.files.models import File
from apps.users.models import MetaxUser

from .meta import CatalogRecord, OtherIdentifier

logger = logging.getLogger(__name__)


class DatasetVersions(AbstractBaseModel):
    """A collection of dataset's versions."""


class Dataset(V2DatasetMixin, CatalogRecord):
    """A collection of data available for access or download in one or many representations.

    RDF Class: dcat:Dataset

    Source: [DCAT Version 3, Draft 11, Dataset](https://www.w3.org/TR/vocab-dcat-3/#Class:Dataset)

    Attributes:
        access_rights (AccessRights): AccessRights ForeignKey relation
        cumulation_ended (models.DateTimeField): When cumulation has ended
        cumulation_started (models.DateTimeField): When cumulation has started
        cumulative_state (models.IntegerField): Is dataset cumulative
        description (HStoreField): Description of the dataset
        draft_revision (models.IntegerField): Draft number
        field_of_science (models.ManyToManyField): FieldOfScience ManyToMany relation
        deprecated (models.DateTimeField): Is the dataset deprecated
        issued (models.DateTimeField): Publication date of the dataset
        keyword (ArrayField): Dataset keywords
        language (models.ManyToManyField): Language ManyToMany relation
        last_cumulative_addition (models.DateTimeField): Last time cumulative record was updated
        other_identifiers (models.ManyToManyField): Other external identifiers for the dataset
        persistent_identifier (models.CharField): Resolvable persistent identifier
        published_revision (models.IntegerField): Published revision number
        preservation_state (models.IntegerField): Number that represents
            long term preservation state of the dataset
        state (models.CharField): Is the dataset published or in draft state
        theme (models.ManyToManyField): Keyword ManyToMany relation
        title (HStoreField): Title of the dataset
    """

    history = HistoricalRecords()

    # Model nested copying configuration
    copier = ModelCopier(
        copied_relations=[
            "access_rights",
            "other_identifiers",
            "actors",
            "provenance",
            "projects",
            "file_set",
            "spatial",
            "temporal",
            "remote_resources",
            "relation",
            "preservation",
        ]
    )

    persistent_identifier = models.CharField(max_length=255, null=True, blank=True)
    issued = models.DateField(
        null=True,
        blank=True,
        help_text="Date of formal issuance (e.g., publication) of the resource.",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', blank=True, null=True
    )

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
    access_rights = models.OneToOneField(
        AccessRights,
        on_delete=models.SET_NULL,
        related_name="dataset",
        null=True,
    )
    other_identifiers = models.ManyToManyField(
        OtherIdentifier,
        blank=True,
    )
    bibliographic_citation = models.TextField(
        help_text="Preferred bibliographic citation.",
        validators=[MinLengthValidator(1)],
        null=True,
        blank=True,
    )
    deprecated = models.DateTimeField(null=True, blank=True)
    cumulation_started = models.DateTimeField(null=True, blank=True)
    cumulation_ended = models.DateTimeField(null=True, blank=True)
    last_cumulative_addition = models.DateTimeField(null=True, blank=True)

    class PIDTypes(models.TextChoices):
        URN = "URN", _("URN")
        DOI = "DOI", _("DOI")

    pid_type = models.CharField(
        max_length=4,
        choices=PIDTypes.choices,
        null=True,
        blank=True,
    )

    class StateChoices(models.TextChoices):
        PUBLISHED = "published", _("Published")
        DRAFT = "draft", _("Draft")

    state = models.CharField(
        max_length=10,
        choices=StateChoices.choices,
        default=StateChoices.DRAFT,
    )
    version = models.IntegerField(default=1, blank=True, editable=False)

    dataset_versions = models.ForeignKey(
        DatasetVersions, related_name="datasets", on_delete=models.SET_NULL, null=True
    )
    history = SnapshotHistoricalRecords(
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

    draft_of = models.OneToOneField(
        "self", related_name="next_draft", on_delete=models.CASCADE, null=True, blank=True
    )

    is_prefetched = False  # Should be set to True when using prefetch_related

    # Fields that should be prefetched with prefetch_related
    common_prefetch_fields = (
        "access_rights__access_type",
        "access_rights__license__reference",
        "access_rights__license",
        "access_rights__restriction_grounds",
        "access_rights",
        "actors__organization__homepage",
        "actors__organization__parent__homepage",
        "actors__organization__parent",
        "actors__organization",
        "actors__person__homepage",
        "actors__person",
        "actors",
        "data_catalog",
        "dataset_versions",
        "draft_of",
        "field_of_science",
        "file_set",
        "infrastructure",
        "language",
        "metadata_owner__user",
        "metadata_owner",
        "next_draft",
        "other_identifiers__identifier_type",
        "other_identifiers",
        "preservation",
        "projects__funding__funder__funder_type",
        "projects__funding__funder__organization__homepage",
        "projects__funding__funder__organization__parent__homepage",
        "projects__funding__funder__organization__parent",
        "projects__funding__funder__organization",
        "projects__funding__funder",
        "projects__funding",
        "projects__participating_organizations__homepage",
        "projects__participating_organizations__parent__homepage",
        "projects",
        "provenance__event_outcome",
        "provenance__is_associated_with__organization__homepage",
        "provenance__is_associated_with__organization__parent__homepage",
        "provenance__is_associated_with__organization__parent",
        "provenance__is_associated_with__organization",
        "provenance__is_associated_with__person__homepage",
        "provenance__is_associated_with__person",
        "provenance__is_associated_with",
        "provenance__lifecycle_event",
        "provenance__spatial__reference",
        "provenance__spatial",
        "provenance__temporal",
        "provenance__used_entity__type",
        "provenance__used_entity",
        "provenance__variables__concept",
        "provenance__variables__universe",
        "provenance__variables",
        "provenance",
        "relation__entity__type",
        "relation__entity",
        "relation__relation_type",
        "relation",
        "remote_resources__file_type",
        "remote_resources__use_category",
        "remote_resources",
        "spatial__provenance",
        "spatial__reference",
        "spatial",
        "temporal",
        "theme",
    )

    is_legacy = models.BooleanField(
        default=False, help_text="Is the dataset migrated from legacy Metax"
    )

    def __init__(self, *args, **kwargs):
        if kwargs.pop("_saving_legacy", None):
            self._saving_legacy = True
        super().__init__(*args, **kwargs)

    def has_permission_to_edit(self, user: MetaxUser):
        if user.is_superuser:
            return True
        elif not user.is_authenticated:
            return False
        elif user == self.system_creator:
            return True
        elif self.metadata_owner and self.metadata_owner.user == user:
            return True
        elif self.data_catalog and DataCatalogAccessPolicy().query_object_permission(
            user=user, object=self.data_catalog, action="<op:admin_dataset>"
        ):
            return True
        return False

    def has_permission_to_see_drafts(self, user: MetaxUser):
        return self.has_permission_to_edit(user)

    @staticmethod
    def _historicals_to_instances(historicals):
        return [historical.instance for historical in historicals if historical.instance]

    @property
    def next_existing_version(self):
        return (
            self.dataset_versions.datasets.order_by("created")
            .filter(version__gt=self.version)
            .first()
        )

    @cached_property
    def latest_published_revision(self):
        return self.get_revision(publication_number=self.published_revision)

    @cached_property
    def first_published_revision(self):
        return self.get_revision(publication_number=1)

    @property
    def has_files(self):
        return hasattr(self, "file_set") and self.file_set.files.exists()

    @property
    def has_published_files(self):
        """Return true if dataset or its draft_of dataset has published files."""
        if self.state == Dataset.StateChoices.DRAFT:
            if pub := getattr(self, "draft_of", None):
                return pub.has_published_files
            return False
        return self.has_files

    @property
    def allow_adding_files(self) -> bool:
        """Return true if files can be added to dataset."""
        if self.state == Dataset.StateChoices.DRAFT:
            if pub := getattr(self, "draft_of", None):
                # Published dataset determines if files can be added
                return pub.allow_adding_files
            return True

        # Published dataset has to be cumulative or empty to allow adding files
        return self.cumulative_state == self.CumulativeState.ACTIVE or not self.has_files

    @property
    def allow_removing_files(self) -> bool:
        """Return true if files can be removed from dataset."""
        return not self.has_published_files

    def get_revision(self, name: str = None, publication_number: int = None):
        revision = None
        if publication_number:
            revision = self.history.filter(
                history_change_reason=f"published-{publication_number}"
            ).first()
        elif name:
            revision = self.history.filter(history_change_reason=name).first()
        if revision:
            return revision.instance

    def all_revisions(self, as_instance_list=False):
        revisions = self.history.all()
        if as_instance_list:
            return self._historicals_to_instances(revisions)
        else:
            return revisions.as_instances()

    def create_copy(self, **kwargs) -> Self:
        """Creates a copy of the given dataset and its related objects.

        This method is used when a dataset is being published as a new version.

        Args:
            original (Dataset): The original dataset to be copied
            **kwargs: New values to assign to the copy

        Returns:
            Dataset: The copied dataset
        """
        new_values = dict(
            preservation=None,
            state=self.StateChoices.DRAFT,
            published_revision=0,
            created=timezone.now(),
            modified=timezone.now(),
            persistent_identifier=None,
            draft_of=None,
            api_version=3,
        )
        new_values.update(kwargs)
        copy = self.copier.copy(self, new_values=new_values)
        return copy

    def create_new_version(self) -> Self:
        self._deny_if_versioning_not_allowed()
        latest_version = (
            self.dataset_versions.datasets(manager="all_objects").order_by("version").last()
        )
        copy = self.create_copy(version=latest_version.version + 1)
        copy.create_snapshot(created=True)
        return copy

    def check_new_draft_allowed(self):
        if self.state != self.StateChoices.PUBLISHED:
            raise ValidationError(
                {"state": _("Dataset needs to be published before creating a new draft.")}
            )
        if getattr(self, "next_draft", None):
            raise ValidationError({"next_draft": _("Dataset already has a draft.")})

    def create_new_draft(self) -> Self:
        self.check_new_draft_allowed()
        copy = self.create_copy(
            draft_of=self,
            draft_revision=0,
            persistent_identifier=f"draft:{self.persistent_identifier}",
        )
        copy.create_snapshot(created=True)
        return copy

    def _check_merge_draft_files(self):
        """Check that merging draft would not cause invalid file changes."""
        dft = self.next_draft
        no_files = File.objects.none()
        self_files = (getattr(self, "file_set", None) and self.file_set.files.all()) or no_files
        dft_files = (getattr(dft, "file_set", None) and dft.file_set.files.all()) or no_files
        files_removed = self_files.difference(dft_files).exists()
        if files_removed:
            raise ValidationError(
                {"fileset": _("Merging changes would remove files, which is not allowed.")}
            )
        files_added = dft_files.difference(self_files).exists()
        if files_added and self.cumulative_state != self.CumulativeState.ACTIVE:
            raise ValidationError(
                {"fileset": _("Merging changes would add files, which is not allowed.")}
            )

    def merge_draft(self):
        """Merge values from next_draft dataset and delete the draft."""
        if not self.next_draft:
            raise ValidationError({"state": _("Dataset does not have a draft.")})
        if self.next_draft.deprecated:
            raise ValidationError({"state": _("Draft is deprecated.")})

        self._check_merge_draft_files()
        dft = self.next_draft
        ignored_values = [
            "id",
            "catalogrecord_ptr",
            "state",
            "published_revision",
            "created",
            "persistent_identifier",
            "next_draft",
            "draft_of",
            "metadata_owner",
            "other_versions",
            "legacydataset",
            "preservation",
            "draft_revision",
        ]

        for field in self._meta.get_fields():
            if field.name in ignored_values:
                continue

            if field.is_relation and not field.many_to_one:
                if field.many_to_many:
                    # Many-to-many can be set with manager
                    manager = getattr(self, field.name)
                    manager.set(getattr(dft, field.name).all())
                elif field.one_to_many or (field.one_to_one and not field.concrete):
                    # Field value in related table, reassign draft dataset relations
                    remote_field = field.remote_field.name
                    old_relations = field.related_model.all_objects.filter(
                        **{remote_field: self.id}
                    )
                    old_relations.delete()  # Hard delete old related objects
                    draft_relations = field.related_model.objects.filter(**{remote_field: dft.id})
                    draft_relations.update(**{remote_field: self.id})

                elif field.one_to_one and field.concrete:
                    # Unique field value in model table, value must be removed from draft first
                    dft_value = getattr(dft, field.name)
                    setattr(self, field.name, dft_value)
                    setattr(dft, field.name, None)
            else:
                # Field value in model table, can be assigned directly
                dft_value = getattr(dft, field.name)
                setattr(self, field.name, dft_value)

        dft.draft_of = None
        # Update draft to remove unique one-to-one values, skip Dataset.save to avoid validation
        models.Model.save(dft)
        self.save()
        self.next_draft = None  # Remove cached related object
        dft.delete(soft=False)
        self.create_snapshot()

    def delete(self, *args, **kwargs):
        # Drafts are always hard deleted
        if self.state == self.StateChoices.DRAFT:
            kwargs["soft"] = False

        if self.access_rights:
            self.access_rights.delete(*args, **kwargs)

        _deleted = super().delete(*args, **kwargs)
        if "soft" in kwargs and kwargs["soft"] is True:
            post_delete.send(Dataset, instance=self, soft=True)
        return _deleted

    def _validate_cumulative_state(self):
        """Check to prevent changing non-cumulative to cumulative

        Raises:
            ValidationError: If the cumulative state cannot be changed.
        """
        public_state = None  # Published cumulative state of dataset
        if self.state == self.StateChoices.PUBLISHED:
            public_state = self.tracker.previous("cumulative_state")
        elif self.draft_of:
            public_state = self.draft_of.cumulative_state

        allowed_states: set
        if public_state is None:
            allowed_states = {self.CumulativeState.NOT_CUMULATIVE, self.CumulativeState.ACTIVE}
        else:
            allowed_states = {public_state}
            if public_state == self.CumulativeState.ACTIVE:
                allowed_states.add(self.CumulativeState.CLOSED)

        if self.cumulative_state not in allowed_states:
            raise ValidationError(
                {
                    "cumulative_state": "Cannot change state to {state}.".format(
                        state=self.cumulative_state
                    )
                }
            )

    def _update_cumulative_state(self):
        """Update fields related to cumulative state."""
        self._validate_cumulative_state()
        if self.state == self.StateChoices.PUBLISHED:
            if self.cumulative_state == self.CumulativeState.ACTIVE:
                self.cumulation_started = self.cumulation_started or timezone.now()
            elif self.cumulative_state == self.CumulativeState.CLOSED:
                self.cumulation_ended = self.cumulation_ended or timezone.now()

    def _deny_if_versioning_not_allowed(self):
        """Checks whether new versions of this dataset can be created.

        Requirements:
        Dataset is not a legacy dataset.
        Dataset belongs to a data catalog that supports versioning.
        Dataset is not a draft.
        Dataset has not been removed.
        Dataset is the latest existing version of its version set.
        Dataset does not have an existing draft for a new version.

        Raises:
            ValidationError: If any of the versioning requirements are not met.
        """
        from apps.core.models import LegacyDataset

        errors = {}

        if isinstance(self, LegacyDataset):
            errors["dataset"] = _("Cannot create a new version of a legacy dataset.")
        if not (self.data_catalog and self.data_catalog.dataset_versioning_enabled):
            errors["data_catalog"] = _("Data catalog doesn't support versioning.")
        if self.removed is not None:
            errors["removed"] = _("Cannot make a new version of a removed dataset.")
        if self.state == self.StateChoices.DRAFT:
            errors["state"] = _("Cannot make a new version of a draft.")
        if self.next_existing_version is not None:
            if self.next_existing_version.state == self.StateChoices.DRAFT:
                errors["dataset_versions"] = _(
                    "There is an existing draft of a new version of this dataset."
                )
            else:
                errors["dataset_versions"] = _(
                    "Newer version of this dataset exists. Only the latest existing version of the dataset can be used to make a new version."
                )

        if errors:
            raise ValidationError(errors)
        else:
            return False

    def _can_create_urn(self):
        return self.pid_type == self.PIDTypes.URN

    def set_update_reason(self, reason: str):
        """Set change reason used by simple-history."""
        self._change_reason = reason

    def create_persistent_identifier(self):
        if self.persistent_identifier != None:
            logger.info("Dataset already has a PID. PID is not created")
            return
        if self.state == self.StateChoices.DRAFT:
            logger.info("State is DRAFT. PID is not created")
            return
        if self.pid_type == self.PIDTypes.URN and self._can_create_urn():
            dataset_id = self.id
            try:
                pid = PIDMSClient.createURN(dataset_id)
                self.persistent_identifier = pid
            except ServiceUnavailableError as e:
                e.detail = f"Error when creating persistent identifier. Please try again later."
                raise e

    def publish(self):
        """Publishes the dataset.

        If the dataset is a linked draft, merges
        it to the original published dataset and returns
        the published dataset.

        Returns:
            Dataset: The published dataset."""
        if self.state == self.StateChoices.DRAFT:
            if original := self.draft_of:
                # Dataset is a draft, merge it to original
                original.merge_draft()
                return original

        self.state = self.StateChoices.PUBLISHED
        if not self.persistent_identifier:
            self.validate_published(require_pid=False)  # Don't create pid for invalid dataset
            self.create_persistent_identifier()

        if not self.issued:
            self.issued = datetime_to_date(timezone.now())

        # Remove historical draft revisions when publishing
        self.history.filter(state=self.StateChoices.DRAFT).delete()
        self.save()
        self.create_snapshot()
        return self

    def validate_published(self, require_pid=True):
        """Validates that dataset is acceptable for publishing.

        Args:
            require_pid: Is persistent_identifier required.

        Raises:
            ValidationError: If dataset has invalid or missing fields.
        """
        errors = {}
        actor_errors = []
        access_rights_errors = []

        if not self.data_catalog:
            errors["data_catalog"] = _("Dataset has to have a data catalog when publishing.")
        if require_pid and not self.persistent_identifier:
            errors["persistent_identifier"] = _(
                "Dataset has to have a persistent identifier when publishing."
            )
        if not self.access_rights:
            errors["access_rights"] = _("Dataset has to have access rights when publishing.")
        if not self.description:
            errors["description"] = _("Dataset has to have a description when publishing.")

        # Some legacy/harvested datasets are missing creator or publisher
        # Some legacy datasets are also missing license or restriction grounds
        is_harvested = self.data_catalog and self.data_catalog.harvested
        if not (self.is_legacy and is_harvested):
            if self.actors.filter(roles__contains=["creator"]).count() <= 0:
                actor_errors.append(_("An actor with creator role is required."))
                errors["actors"] = actor_errors
        if not self.is_legacy:
            if self.actors.filter(roles__contains=["publisher"]).count() != 1:
                actor_errors.append(_("Exactly one actor with publisher role is required."))
                errors["actors"] = actor_errors
            if self.access_rights and not self.access_rights.license.exists():
                access_rights_errors.append(_("Dataset has to have a license when publishing."))
                errors["access_rights"] = access_rights_errors
            if (
                self.access_rights
                and self.access_rights.access_type.url != AccessTypeChoices.OPEN
                and not self.access_rights.restriction_grounds.exists()
            ):
                access_rights_errors.append(
                    _(
                        "Dataset access rights has to contain restriction grounds if access type is not 'Open'."
                    )
                )
                errors["access_rights"] = access_rights_errors
            if (
            self.access_rights
            and self.access_rights.access_type.url == AccessTypeChoices.OPEN
            and self.access_rights.restriction_grounds.exists()
            ):
                access_rights_errors.append(_("Open datasets do not accept restriction grounds."))
                errors["access_rights"] = access_rights_errors

        if errors:
            raise ValidationError(errors)

    def validate_unique_fields(self):
        """Validate uniqueness constraints."""
        if self.persistent_identifier and self.data_catalog:
            # Validate pid. Note that there is no DB constraint for this
            # because data_catalog and persistent_identifier live
            # in separate tables.
            if (
                Dataset.all_objects.exclude(id=self.id)
                .filter(
                    data_catalog=self.data_catalog,
                    persistent_identifier=self.persistent_identifier,
                )
                .exists()
            ):
                raise ValidationError(
                    {
                        "persistent_identifier": _(
                            "Data catalog is not allowed to have multiple datasets with same value."
                        )
                    }
                )

    def validate_allow_remote_resources(self):
        """Raise error if dataset cannot have remote resources."""
        catalog: DataCatalog = self.data_catalog
        allow_remote_resources = catalog and catalog.allow_remote_resources
        if not allow_remote_resources:
            err_msg = f"Data catalog {catalog.id} does not allow remote resources."
            raise TopLevelValidationError({"remote_resources": err_msg})

    def validate_allow_storage_service(self, storage_service):
        """Raise error if dataset cannot have files from storage_service."""
        catalog: DataCatalog = self.data_catalog
        allowed_storage_services = catalog and catalog.storage_services or []
        if storage_service not in allowed_storage_services:
            err_msg = (
                f"Data catalog {catalog.id} does not allow files from service {storage_service}."
            )
            raise TopLevelValidationError({"fileset": {"storage_service": err_msg}})

    def validate_catalog(self):
        """Data catalog specific validation of dataset fields."""
        if self._state.adding:
            return  # Reverse relations are not yet available

        if self.remote_resources.exists():
            self.validate_allow_remote_resources()

        if fileset := getattr(self, "file_set", None):
            self.validate_allow_storage_service(fileset.storage_service)

    def ensure_prefetch(self):
        """Ensure related fields have been prefetched."""
        if not self.is_prefetched:
            models.prefetch_related_objects([self], *self.common_prefetch_fields)
            self.is_prefetched = True

    def save(self, *args, **kwargs):
        """Saves the dataset and increments the draft or published revision number as needed."""
        self.validate_unique_fields()
        self.validate_catalog()
        if not getattr(self, "_saving_legacy", False):
            self._update_cumulative_state()

        # Prevent changing state of a published dataset
        previous_state = self.tracker.previous("state")
        if not self._state.adding:
            if previous_state == self.StateChoices.PUBLISHED and self.state != previous_state:
                raise ValidationError({"state": _("Cannot change value into non-published.")})

        if not self.dataset_versions:
            self.dataset_versions = DatasetVersions.objects.create()
        if self.state == self.StateChoices.DRAFT:
            self.draft_revision += 1
        elif self.state == self.StateChoices.PUBLISHED:
            self.published_revision += 1
            self.draft_revision = 0
            self.validate_published()

        self.set_update_reason(f"{self.state}-{self.published_revision}.{self.draft_revision}")
        super().save(*args, **kwargs)
        self.is_prefetched = False  # Saving clears the prefetch cache
        if hasattr(self, "file_set"):
            self.file_set.update_published()

    def signal_update(self, created=False):
        """Send dataset_update or dataset_created signal."""
        from apps.core.signals import dataset_created, dataset_updated

        if created:
            return dataset_created.send(sender=self.__class__, data=self)
        return dataset_updated.send(sender=self.__class__, data=self)
