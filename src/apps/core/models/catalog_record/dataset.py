import logging

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from model_utils import FieldTracker
from rest_framework.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from simple_history.utils import update_change_reason
from typing_extensions import Self

from apps.common.copier import ModelCopier
from apps.common.helpers import datetime_to_date, prepare_for_copy
from apps.common.models import AbstractBaseModel
from apps.core.mixins import V2DatasetMixin
from apps.core.models.access_rights import AccessRights
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.services.pid_ms_client import PIDMSClient, ServiceUnavailableError

from .meta import CatalogRecord, OtherIdentifier

logger = logging.getLogger(__name__)


class Dataset(V2DatasetMixin, CatalogRecord, AbstractBaseModel):
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

    # Model nested copying configuration
    copier = ModelCopier(
        copied_relations=[
            "access_rights",
            "other_identifiers",
            "actors",
            "provenance",
            # "projects",
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
    deprecated = models.DateTimeField(null=True)
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
    # First, last replaces, next

    other_versions = models.ManyToManyField("self", db_index=True, blank=True)
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

    draft_of = models.OneToOneField(
        "self", related_name="next_draft", on_delete=models.CASCADE, null=True, blank=True
    )

    def has_permission_to_see_drafts(self, user: settings.AUTH_USER_MODEL, blank=True, null=True):
        if user.is_superuser:
            return True
        elif not user.is_authenticated:
            return False
        elif user == self.system_creator:
            return True
        elif self.metadata_owner:
            if self.metadata_owner.user == user:
                return True
        return False

    @staticmethod
    def _historicals_to_instances(historicals):
        return [historical.instance for historical in historicals if historical.instance]

    @cached_property
    def latest_published_revision(self):
        return self.get_revision(publication_number=self.published_revision)

    @cached_property
    def first_published_revision(self):
        return self.get_revision(publication_number=1)

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

    def all_revisions(self, published_only=False, draft_only=False, as_instance_list=False):
        revisions = []
        if published_only:
            revisions = self.history.filter(history_change_reason__contains="published-")
        elif draft_only:
            revisions = self.history.filter(history_change_reason__contains="draft-")
        else:
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
            catalogrecord_ptr=None,
            state=self.StateChoices.DRAFT,
            published_revision=0,
            created=timezone.now(),
            modified=timezone.now(),
            persistent_identifier=None,
            draft_of=None,
        )
        new_values.update(kwargs)
        copy = self.copier.copy(self, new_values=new_values)
        return copy

    def create_new_version(self) -> Self:
        copy = self.create_copy()
        copy.other_versions.add(self)
        for version in self.other_versions.exclude(id=copy.id):
            copy.other_versions.add(version)
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
        copy = self.create_copy(draft_of=self)
        return copy

    def delete(self, *args, **kwargs):
        if self.access_rights:
            self.access_rights.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)

    def _deny_if_trying_to_change_to_cumulative(self) -> bool:
        """Check to prevent changing non-cumulative to cumulative

        Raises:
            ValidationError: If the cumulative state cannot be changed.

        Returns:
            bool: False if not trying to change non-cumulative to cumulative

        """
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
        """Checks if the published_revision number should be increased.

        Returns:
            bool: True if the published revision should be increased, False otherwise.
        """
        state_has_changed, previous_state = self.tracker.has_changed(
            "state"
        ), self.tracker.previous("state")
        if not self.persistent_identifier:
            logger.info(f"Dataset {self.id} has no persistent_identifier. Not publishing")
            return False
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
        """Checks if the draft_revision number should be increased.

        Returns:
            bool: True if the draft revision should be increased, False otherwise.
        """
        state_has_changed, previous_state = self.tracker.has_changed(
            "state"
        ), self.tracker.previous("state")
        if (
            state_has_changed
            and previous_state == self.StateChoices.DRAFT
            and self.state == self.StateChoices.DRAFT
            or previous_state == self.StateChoices.PUBLISHED
            and self.state == self.StateChoices.DRAFT
            and self.published_revision != 0
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

    def _can_create_urn(self):
        return self.pid_type == self.PIDTypes.URN

    def change_update_reason(self, reason: str):
        from apps.core.models import LegacyDataset

        if not isinstance(self, LegacyDataset):
            update_change_reason(self, reason)

    def create_persistent_identifier(self):
        if self.state == self.StateChoices.DRAFT:
            logger.info("State is DRAFT. PID is not created")
            return
        if self.persistent_identifier != None:
            return
        if self.pid_type == self.PIDTypes.URN and self._can_create_urn():
            dataset_id = self.id
            try:
                pid = PIDMSClient.createURN(dataset_id)
                self.persistent_identifier = pid
                self.save()
            except ServiceUnavailableError as e:
                e.detail = f"Error when creating persistent identifier. Please try again later."
                raise e

    def publish(self):
        """Publishes the dataset by creating a new revision and setting the
        `issued` date to the current time if not set.

        The `persistent_identifier` must be set
        before publishing.

        Raises:
            ValidationError: If the dataset does not have a persistent identifier.
        """
        errors = {}
        if not self.data_catalog:
            errors["data_catalog"] = _("Dataset has to have a data catalog when publishing")
        if not self.persistent_identifier:
            errors["persistent_identifier"] = _(
                "Dataset has to have a persistent identifier when publishing"
            )
        if not self.access_rights:
            errors["access_rights"] = _("Dataset has to have access rights when publishing")
        if errors:
            raise ValidationError(errors)
        self.published_revision += 1
        self.draft_revision = 0
        if not self.issued:
            self.issued = datetime_to_date(timezone.now())
        return True

    def validate_unique(self):
        """Validate uniqueness constraints."""
        if self.persistent_identifier and self.data_catalog:
            # Validate pid. Note that there is no DB constraint for this
            # because data_catalog and persistent_identifier live
            # in separate tables.
            if (
                Dataset.available_objects.exclude(id=self.id)
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

    def save(self, *args, **kwargs):
        """Saves the dataset and increments the draft or published revision number as needed.

        The function will also publish a new version  or
        increment the draft revision number as appropriate.
        """
        self.validate_unique()
        self._deny_if_trying_to_change_to_cumulative()

        published_version_changed = False
        draft_version_changed = False
        if self._should_increase_published_revision():
            published_version_changed = self.publish()
        if self._should_increase_draft_revision():
            draft_version_changed = True
            self.draft_revision += 1
        super().save(*args, **kwargs)
        if published_version_changed:
            self.change_update_reason(f"{self.state}-{self.published_revision}")
        elif draft_version_changed:
            self.change_update_reason(
                f"{self.state}-{self.published_revision}.{self.draft_revision}"
            )
