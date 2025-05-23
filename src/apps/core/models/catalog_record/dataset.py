import logging
from typing import Optional
from uuid import UUID

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MinLengthValidator
from django.db import models, transaction
from django.db.models import prefetch_related_objects
from django.db.models.signals import post_delete
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from model_utils import FieldTracker
from rest_framework.exceptions import ValidationError
from typing_extensions import Self
from watson.search import skip_index_update

from apps.common.copier import ModelCopier
from apps.common.exceptions import TopLevelValidationError
from apps.common.helpers import datetime_to_date, normalize_doi
from apps.common.history import SnapshotHistoricalRecords
from apps.common.models import AbstractBaseModel
from apps.common.tasks import run_task
from apps.core.models.access_rights import AccessRights, AccessTypeChoices
from apps.core.models.catalog_record.dataset_permissions import DatasetPermissions
from apps.core.models.concepts import (
    FieldOfScience,
    IdentifierType,
    Language,
    ResearchInfra,
    Theme,
)
from apps.core.models.data_catalog import DataCatalog, GeneratedPIDType
from apps.core.models.mixins import V2DatasetMixin
from apps.core.models.preservation import Preservation
from apps.core.services.pid_ms_client import PIDMSClient, ServiceUnavailableError
from apps.files.models import File
from apps.rems.rems_service import REMSService
from apps.users.models import MetaxUser

from .meta import CatalogRecord, OtherIdentifier

logger = logging.getLogger(__name__)


class REMSStatus(models.TextChoices):
    """Dataset REMS status."""

    NOT_REMS = "not_rems", "Not REMS dataset"
    PUBLISHED = "published", "Published to REMS"
    NOT_PUBLISHED = "not_published", "Not published to REMS"
    ERROR = "error", "Publish to REMS failed"


class REMSApplicationStatus(models.TextChoices):
    """Dataset REMS status."""

    DISABLED = "disabled", "REMS disabled"
    NOT_REMS_USER = "not_rems_user", "REMS disabled for user"
    NOT_IN_REMS = "not_in_rems", "Dataset not published in REMS"
    NO_APPLICATION = "no_application", "No active applications"
    DRAFT = "draft", "Application incomplete"
    SUBMITTED = "submitted", "Application submitted"
    APPROVED = "approved", "REMS application approved"
    REJECTED = "rejected", "REMS application rejected"


class DatasetVersions(AbstractBaseModel):
    """A collection of dataset's versions."""

    # List of ids of legacy datasets belonging to set. May contain ids
    # of datasets that haven't been migrated yet.
    legacy_versions = ArrayField(models.UUIDField(), default=list, blank=True)


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

    persistent_identifier = models.CharField(max_length=255, null=True, blank=True, db_index=True)
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
    )
    theme = models.ManyToManyField(Theme, related_name="datasets", blank=True)
    field_of_science = models.ManyToManyField(FieldOfScience, related_name="datasets", blank=True)
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
    generate_pid_on_publish = models.CharField(
        max_length=4,
        choices=GeneratedPIDType.choices,
        null=True,
        blank=True,
    )
    pid_generated_by_fairdata = models.BooleanField(default=False)

    class StateChoices(models.TextChoices):
        PUBLISHED = "published", _("Published")
        DRAFT = "draft", _("Draft")

    state = models.CharField(
        max_length=10,
        choices=StateChoices.choices,
        default=StateChoices.DRAFT,
    )

    dataset_versions = models.ForeignKey(
        DatasetVersions, related_name="datasets", on_delete=models.SET_NULL, null=True
    )
    permissions = models.ForeignKey(
        DatasetPermissions, related_name="datasets", on_delete=models.SET_NULL, null=True
    )
    history = SnapshotHistoricalRecords(
        m2m_fields=(language, theme, field_of_science, infrastructure, other_identifiers),
        excluded_fields=["permissions", "rems_publish_error"],
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

    rems_publish_error = models.TextField(null=True, blank=True)

    is_prefetched = False  # Should be set to True when using prefetch_related

    # Fields that may be requested when checking dataset editing permissions
    permissions_prefetch_fields = (
        "data_catalog",
        "data_catalog__dataset_groups_admin",
        "data_catalog__dataset_groups_create",
        "file_set",
        "file_set__storage",
        "metadata_owner",
        "metadata_owner__user",
        "permissions",
        "permissions__editors",
    )
    # Fields that should be prefetched with prefetch_related
    common_prefetch_fields = (
        *permissions_prefetch_fields,
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
        "dataset_versions",
        "draft_of",
        "field_of_science",
        "infrastructure",
        "language",
        "next_draft",
        "other_identifiers__identifier_type",
        "other_identifiers",
        "preservation",
        "preservation__dataset_version__dataset",
        "preservation__dataset_origin_version__dataset",
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

    dataset_versions_prefetch_fields = (
        *permissions_prefetch_fields,
        "draft_of",
        "next_draft",
    )

    @classmethod
    def get_versions_prefetch(cls):
        return models.Prefetch(
            "dataset_versions__datasets",
            queryset=cls.all_objects.order_by("-created").prefetch_related(
                *cls.dataset_versions_prefetch_fields
            ),
            to_attr="_datasets",
        )

    is_legacy = models.BooleanField(
        default=False, help_text="Is the dataset migrated from legacy Metax"
    )

    def __init__(self, *args, **kwargs):
        """Init Dataset instance.

        Arguments:
            _saving_legacy (bool): Skip some validation on save when enabled.
        """
        if val := kwargs.pop("_saving_legacy", None):
            self._saving_legacy = val
        super().__init__(*args, **kwargs)

    def has_permission_to_edit(self, user: MetaxUser) -> bool:
        """Determine if user has permission to edit dataset."""
        if user.is_superuser:
            return True
        elif not user.is_authenticated:
            return False
        elif user == self.system_creator:
            return True
        elif self.metadata_owner and self.metadata_owner.user == user:
            return True
        elif (
            fileset := getattr(self, "file_set", None)
        ) and fileset.storage.csc_project in user.csc_projects:
            return True
        elif self.permissions and user in self.permissions.editors.all():
            return True
        elif self.data_catalog and self.data_catalog.can_admin_datasets(user):
            return True
        return False

    def get_lock_reason(self, user: MetaxUser) -> Optional[str]:
        """Determine if and why user is locked from modifying the dataset."""
        if user.is_superuser:
            return None
        if (
            self.preservation
            and self.preservation.pas_process_running
            and not any(group.name == "pas" for group in user.groups.all())
        ):
            return (
                "Only PAS service is allowed to modify "
                "the dataset while PAS process is running."
            )

        return None

    def has_permission_to_see_drafts(self, user: MetaxUser):
        return self.has_permission_to_edit(user)

    def has_rems_entitlement(self, user: MetaxUser) -> bool:
        if not settings.REMS_ENABLED:
            return False
        if not getattr(user, "fairdata_username", None):
            return False
        return len(REMSService().get_user_entitlements_for_dataset(user=user, dataset=self)) > 0

    def get_user_rems_application_status(self, user: MetaxUser):
        if not settings.REMS_ENABLED:
            return REMSApplicationStatus.DISABLED
        if not getattr(user, "fairdata_username", None):
            return REMSApplicationStatus.NOT_REMS_USER
        if self.rems_status != REMSStatus.PUBLISHED:
            return REMSApplicationStatus.NOT_IN_REMS

        # entitlement: the right of a user to access a resource
        service = REMSService()
        if self.has_rems_entitlement(user):
            return REMSApplicationStatus.APPROVED

        applications = service.get_user_applications_for_dataset(user=user, dataset=self)
        if len(applications) == 0:
            return REMSApplicationStatus.NO_APPLICATION

        latest = sorted(applications, key=lambda a: a["application/created"], reverse=True)[0]
        state = latest["application/state"]
        if state in {"application.state/draft", "application.state/returned"}:
            # draft: application created but not submitted yet
            # returned: handler requests changes to the submitted application.
            return REMSApplicationStatus.DRAFT
        if state == "application.state/submitted":
            # submitted: application waiting for approval
            return REMSApplicationStatus.SUBMITTED
        if state in {"application.state/rejected", "application.state/revoked"}:
            # rejected: application rejected
            # revoked: access rights revoked due to misuse, users have been added to the blacklist
            return REMSApplicationStatus.REJECTED

        # Remaining states are "closed" and "approved"
        # closed: application closed as obsolete
        # approved: application approved but user has no entitlement, maybe approval expired?
        return REMSApplicationStatus.NO_APPLICATION

    @staticmethod
    def _historicals_to_instances(historicals):
        return [historical.instance for historical in historicals if historical.instance]

    # Get dataset that has been created after the current dataset and is not a draft of another dataset
    @property
    def next_existing_version(self):
        return (
            self.dataset_versions.datasets.order_by("created")
            .filter(draft_of__isnull=True)
            .filter(created__gt=self.created)
            .first()
        )

    @cached_property
    def version_number(self):
        # Version number is calculated by checking how many of the published datasets in dataset_versions have been
        # created earlier than the current dataset.
        if versions := getattr(self.dataset_versions, "_datasets", None):  # Prefetched versions
            index = (
                sum(
                    1 if v.created < self.created and v.state == "published" else 0
                    for v in versions
                )
                + 1
            )
        else:
            index = (
                self.dataset_versions.datasets.filter(state="published")
                .filter(created__lt=self.created)
                .count()
                + 1
            )
        # If dataset is a draft of another dataset, then version number is same as the version number of the
        # source dataset. In practice, this means that it is 1 less than otherwise
        if self.draft_of != None:
            index -= 1
        return index

    @cached_property
    def latest_published_revision(self):
        return self.get_revision(publication_number=self.published_revision)

    @cached_property
    def first_published_revision(self):
        return self.get_revision(publication_number=1)

    @property
    def has_files(self):
        return hasattr(self, "file_set") and self.file_set.files(manager="all_objects").exists()

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

    @property
    def is_rems_dataset(self) -> bool:
        return (
            self.state == "published"
            and self.data_catalog.rems_enabled
            and self.access_rights.access_type.url
            in {AccessTypeChoices.PERMIT, AccessTypeChoices.RESTRICTED}
            and self.access_rights.rems_approval_type is not None
        )

    @property
    def rems_id(self) -> Optional[int]:
        if catalogue_item := REMSService().get_dataset(self):
            return catalogue_item.rems_id
        return None

    @property
    def rems_status(self) -> Optional[str]:
        if not settings.REMS_ENABLED:
            return None

        if self.rems_publish_error:
            return REMSStatus.ERROR
        if not self.is_rems_dataset:
            return REMSStatus.NOT_REMS
        if self.rems_id:
            return REMSStatus.PUBLISHED
        return REMSStatus.NOT_PUBLISHED

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
        self.ensure_prefetch()
        cumulative_state = (
            self.cumulative_state
            if self.cumulative_state != self.CumulativeState.CLOSED
            else self.CumulativeState.NOT_CUMULATIVE
        )
        new_values = dict(
            preservation=None,
            state=self.StateChoices.DRAFT,
            cumulative_state=cumulative_state,
            published_revision=0,
            created=timezone.now(),
            modified=timezone.now(),
            deprecated=None,
            persistent_identifier=None,
            pid_generated_by_fairdata=False,
            draft_of=None,
            api_version=3,
            rems_publish_error=None,
        )
        new_values.update(kwargs)
        copy = self.copier.copy(self, new_values=new_values)
        return copy

    def create_new_version(self) -> Self:
        self._deny_if_versioning_not_allowed()
        copy = self.create_copy()
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
            pid_generated_by_fairdata=self.pid_generated_by_fairdata,
        )
        copy.create_snapshot(created=True)
        return copy

    def create_preservation_version(self) -> Self:
        """Create preservation dataset version to PAS catalog and add related links."""
        logger.info(f"Creating new PAS dataset version of dataset {self.id}")

        if (
            not self.preservation
            or self.preservation.state <= self.preservation.PreservationState.NONE
        ):
            raise ValidationError({"detail": "Dataset is not in preservation."})

        if self.preservation.dataset_version:
            raise ValidationError({"detail": "Dataset already has a PAS version."})
        if hasattr(self.preservation, "dataset_origin_version"):
            raise ValidationError({"detail": "Dataset is a PAS version of another dataset."})

        try:
            pas_catalog = DataCatalog.objects.get(id="urn:nbn:fi:att:data-catalog-pas")
        except DataCatalog.DoesNotExist:
            raise ValidationError({"detail": "PAS catalog does not exist."})

        # Copy dataset and related files
        pas_version = self.create_copy(
            dataset_versions=None,
            file_set=None,
            preservation=self.preservation.copier.copy(
                self.preservation, new_values={"preservation_identifier": None}
            ),
            data_catalog=pas_catalog,
            generate_pid_on_publish=GeneratedPIDType.DOI,
        )
        logger.info("Copying file entries to PAS storage_service")
        if fileset := getattr(self, "file_set", None):
            pas_version.file_set = fileset.create_preservation_copy(pas_version)

        # Set original dataset PAS version, clear preservation state
        self.preservation.dataset_version = pas_version.preservation
        self.preservation.state = self.preservation.PreservationState.NONE
        self.preservation.save()

        # Add origin version to preservation version other_identifiers
        pas_version.other_identifiers.add(
            OtherIdentifier.objects.create(
                notation=self.persistent_identifier,
                identifier_type=IdentifierType.get_from_identifier(self.persistent_identifier),
            )
        )

        # Publish the PAS copy
        logger.info("Publishing PAS dataset version")
        pas_version.publish()

        # PAS copy now has a PID, add it to origin version other_identifiers
        self.other_identifiers.add(
            OtherIdentifier.objects.create(
                notation=pas_version.persistent_identifier,
                identifier_type=IdentifierType.get_from_identifier(
                    pas_version.persistent_identifier
                ),
            )
        )

        logger.info("PAS dataset version created with identifier: %s" % pas_version.id)
        return pas_version

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
            "next_draft",
            "draft_of",
            "metadata_owner",
            "other_versions",
            "legacydataset",
            "preservation",
            "draft_revision",
            "sync_status",
        ]

        # Ignore PID from draft if it starts with "draft:"
        if dft.persistent_identifier and dft.persistent_identifier.startswith("draft:"):
            ignored_values.append("persistent_identifier")

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

        with skip_index_update():  # Avoid watson update from temporary draft changes
            dft.draft_of = None
            dft.persistent_identifier = None
            # Update draft to remove unique one-to-one values,
            # skip Dataset.save to avoid validation
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

        # Set modification timestamp so pre_delete signal
        # handlers have it up-to-date.
        self.record_modified = timezone.now()

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

        if (
            self.cumulative_state == self.CumulativeState.ACTIVE
            and self.preservation
            and self.preservation.state > Preservation.PreservationState.INITIALIZED
        ):
            raise ValidationError(
                {"cumulative_state": "Cumulative datasets are not allowed in the PAS process."}
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

    def set_update_reason(self, reason: str):
        """Set change reason used by simple-history."""
        self._change_reason = reason

    def create_persistent_identifier(self):
        if self.persistent_identifier:
            raise ValueError("Dataset already has a PID. PID is not created")
        if self.state == self.StateChoices.DRAFT:
            raise ValueError("Dataset is a draft. PID is not created")

        self.validate_pid_fields()
        dataset_id = self.id
        pid = None
        pid_type = self.generate_pid_on_publish
        try:
            if pid_type == GeneratedPIDType.URN:
                pid = PIDMSClient().create_urn(dataset_id)
            elif pid_type == GeneratedPIDType.DOI:
                pid = PIDMSClient().create_doi(dataset_id)
            else:
                raise ValueError(f"Unknown PID type '{pid_type}'. Cannot create PID.")
        except ServiceUnavailableError as e:
            logger.error(f"Error creating persistent identifier: {e}")
            e.detail = "Error when creating persistent identifier. Please try again later."
            raise e

        if pid:
            self.persistent_identifier = pid
            self.pid_generated_by_fairdata = True

    def publish(self) -> Self:
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
        if self.generate_pid_on_publish and not self.persistent_identifier:
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

        catalog: DataCatalog = self.data_catalog
        if not catalog:
            errors["data_catalog"] = _("Dataset has to have a data catalog when publishing.")
        if require_pid and not self.persistent_identifier:
            errors["persistent_identifier"] = _(
                "Dataset has to have a persistent identifier when publishing."
            )
            if catalog and catalog.allow_generated_pid and not catalog.allow_external_pid:
                errors["generate_pid_on_publish"] = _(
                    "Value is required by the catalog when publishing. "
                )

        if not self.access_rights:
            errors["access_rights"] = _("Dataset has to have access rights when publishing.")
        if not self.description:
            errors["description"] = _("Dataset has to have a description when publishing.")

        # Count roles
        creator_count = 0
        publisher_count = 0
        prefetch_related_objects([self], "actors", "actors__person")  # cache actors
        missing_roles = False
        for actor in self.actors.all():
            if not actor.roles:
                missing_roles = True
            if "publisher" in actor.roles:
                publisher_count += 1
            if "creator" in actor.roles:
                creator_count += 1

        if missing_roles:
            actor_errors.append(
                _("All actors in a published dataset should have at least one role.")
            )

        # Some legacy/external datasets are missing creator or publisher
        # Some legacy datasets are also missing license or restriction grounds
        is_external = self.data_catalog and self.data_catalog.is_external
        if not (self.is_legacy and is_external):
            # Creator required
            if creator_count == 0:
                actor_errors.append(_("An actor with creator role is required."))

        if not self.is_legacy:
            if publisher_count != 1:
                actor_errors.append(_("Exactly one actor with publisher role is required."))
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

        if actor_errors:
            errors["actors"] = actor_errors
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
                    {"persistent_identifier": _("Value already exists in the data catalog")}
                )

            if not getattr(self, "_saving_legacy", False):
                checked_pids = {self.persistent_identifier}
                if normalized_doi := normalize_doi(self.persistent_identifier):
                    checked_pids.add(normalized_doi)

                if (
                    Dataset.all_objects.exclude(id=self.id)
                    .filter(
                        data_catalog__is_external=False,
                        persistent_identifier__in=checked_pids,
                    )
                    .exists()
                ):
                    raise ValidationError(
                        {"persistent_identifier": _("Value already exists in IDA or ATT catalog")}
                    )

    def validate_allow_remote_resources(self):
        """Raise error if dataset cannot have remote resources."""
        catalog: DataCatalog = self.data_catalog
        allow_remote_resources = catalog and catalog.allow_remote_resources
        if not allow_remote_resources:
            catalog_id = self.data_catalog_id
            err_msg = f"Data catalog {catalog_id} does not allow remote resources."
            raise TopLevelValidationError({"remote_resources": err_msg})

    def validate_allow_storage_service(self, storage_service):
        """Raise error if dataset cannot have files from storage_service."""
        catalog: DataCatalog = self.data_catalog
        allowed_storage_services = catalog and catalog.storage_services or []
        if storage_service not in allowed_storage_services:
            catalog_id = self.data_catalog_id
            err_msg = (
                f"Data catalog {catalog_id} does not allow files from service {storage_service}."
            )
            raise TopLevelValidationError({"fileset": {"storage_service": err_msg}})

    def _validate_pid_type(self):
        """Check that requested PID generation is allowed by the catalog."""
        pid_type = self.generate_pid_on_publish
        data_catalog: DataCatalog = self.data_catalog
        if data_catalog and pid_type:
            managed_pid_types = data_catalog.managed_pid_types
            msg = None
            if not managed_pid_types:
                msg = "PID generation is not supported for the catalog."
            if pid_type not in managed_pid_types:
                if managed_pid_types:
                    msg = (
                        f"'{pid_type}' is not a valid choice for catalog {data_catalog.id}. "
                        f"Supported values: {', '.join(managed_pid_types)}"
                    )
                else:
                    msg = "The catalog does not allow PID generation."
            if msg:
                if getattr(self, "_saving_legacy", False):
                    logger.warning(f"Dataset {self.id}, {data_catalog.id=}: {msg}")
                else:
                    raise ValidationError({"generate_pid_on_publish": msg})

    def _validate_pid(self):
        """Check that PID is allowed."""
        data_catalog: DataCatalog = self.data_catalog
        if self.persistent_identifier and not data_catalog:
            msg = "Can't assign persistent_identifier if data_catalog isn't given."
            raise ValidationError({"persistent_identifier": msg})

    def validate_pid_fields(self):
        self._validate_pid_type()
        self._validate_pid()

    def validate_catalog(self):
        """Data catalog specific validation of dataset fields."""
        self.validate_pid_fields()

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

    def ensure_versions_and_permissions(self):
        """Add dataset_versions and permissions to dataset if they are missing."""
        draft_relation = self.draft_of or getattr(self, "next_draft", None)
        if not self.dataset_versions_id:
            if draft_relation:
                self.dataset_versions = draft_relation.dataset_versions
            else:
                self.dataset_versions = DatasetVersions.objects.create()
        if not self.permissions_id:
            if draft_relation:
                self.permissions = draft_relation.permissions
            else:
                self.permissions = DatasetPermissions.objects.create()

        # Ensure related drafts are in the same version set and have same permissions
        if draft_relation:
            if draft_relation.dataset_versions_id != self.dataset_versions_id:
                raise ValueError(
                    "Draft datasets should be in the same dataset_versions as original"
                )
            if draft_relation.permissions_id != self.permissions_id:
                raise ValueError("Draft datasets should have same dataset permissions as original")

    def save(self, *args, **kwargs):
        """Saves the dataset and increments the draft or published revision number as needed."""
        self.validate_catalog()
        self.validate_unique_fields()
        if not getattr(self, "_saving_legacy", False):
            self._update_cumulative_state()

        if self.draft_of and self.state != self.StateChoices.DRAFT:
            raise ValueError("Dataset cannot have draft_of if it is not a draft")

        # Prevent changing state of a published dataset
        previous_state = self.tracker.previous("state")
        if not self._state.adding:
            if previous_state == self.StateChoices.PUBLISHED and self.state != previous_state:
                raise ValidationError({"state": _("Cannot change value into non-published.")})

        self.ensure_versions_and_permissions()

        if self.state == self.StateChoices.DRAFT:
            self.draft_revision += 1
        elif self.state == self.StateChoices.PUBLISHED:
            self.published_revision += 1
            self.draft_revision = 0
            self.validate_published()
            if self.preservation and self.preservation.preservation_identifier is None:
                self.preservation.preservation_identifier = self.persistent_identifier
                self.preservation.save()

        self.set_update_reason(f"{self.state}-{self.published_revision}.{self.draft_revision}")
        super().save(*args, **kwargs)
        self.is_prefetched = False  # Prefetch again after save

        if self.state == self.StateChoices.PUBLISHED and hasattr(self, "file_set"):
            run_task(self.file_set.update_published)

    def signal_update(self, created=False):
        """Send dataset_update or dataset_created signal."""
        from apps.core.signals import dataset_created, dataset_updated

        if created:
            return dataset_created.send(sender=self.__class__, instance=self)
        return dataset_updated.send(sender=self.__class__, instance=self)

    @classmethod
    def lock_for_update(cls, id: UUID):
        """Locks dataset row for update until end of transaction.

        Blocks until lock is acquired. If no matching dataset is found, does nothing.

        If not in transaction, does nothing.
        """
        if transaction.get_autocommit():
            return  # Not in transaction

        try:
            # Ideally we'd call select_for_update in the same query where we fetch the dataset
            # instance but postgres does not support it for queries that use `.distinct()`.
            Dataset.all_objects.select_for_update(of=("self",)).filter(id=id).values("id").first()
        except DjangoValidationError:
            pass  # Invalid UUID
