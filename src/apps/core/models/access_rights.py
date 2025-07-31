import json
import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.copier import ModelCopier
from apps.common.helpers import datetime_to_date
from apps.common.history import SnapshotHistoricalRecords
from apps.common.models import AbstractBaseModel
from apps.core.models.concepts import AccessType, DatasetLicense, RestrictionGrounds
from apps.rems.rems_service import REMSService

if TYPE_CHECKING:
    from apps.core.models import Dataset


class REMSApprovalType(models.TextChoices):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class AccessTypeChoices(models.TextChoices):
    OPEN = "http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
    LOGIN = "http://uri.suomi.fi/codelist/fairdata/access_type/code/login"
    PERMIT = "http://uri.suomi.fi/codelist/fairdata/access_type/code/permit"
    EMBARGO = "http://uri.suomi.fi/codelist/fairdata/access_type/code/embargo"
    RESTRICTED = "http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted"


class AccessRights(AbstractBaseModel):
    """Information about who can access the resource or an indication of its security status.

    RFD Property: dcterms:accessRights

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_access_rights

    Attributes:
        license(models.ManyToManyField): ManyToMany relation to License
        access_type(AccessType): AccessType ForeignKey relation
        description(HStoreField): Description of the access rights
    """

    # Model nested copying configuration
    copier = ModelCopier(copied_relations=["license"], parent_relations=["dataset"])

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ManyToManyField(
        DatasetLicense,
        related_name="access_rights",
    )
    access_type = models.ForeignKey(
        AccessType,
        on_delete=models.SET_NULL,
        related_name="access_rights",
        null=True,
        blank=True,
    )
    restriction_grounds = models.ManyToManyField(RestrictionGrounds, related_name="access_rights")
    available = models.DateField(
        null=True,
        blank=True,
        help_text=("Date (UTC) that the resource became or will become available."),
    )

    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', null=True, blank=True
    )
    rems_approval_type = models.TextField(choices=REMSApprovalType.choices, null=True, blank=True)
    data_access_application_instructions = HStoreField(
        help_text="Instructions for applying for access to the data.",
        null=True,
        blank=True,
    )
    data_access_terms = HStoreField(
        help_text="Terms a user needs to approve before getting access to the data.",
        null=True,
        blank=True,
    )
    data_access_reviewer_instructions = HStoreField(
        help_text="Instructions for data access reviewers. Not shown to applicants.",
        null=True,
        blank=True,
    )
    history = SnapshotHistoricalRecords(m2m_fields=(license,))
    show_file_metadata = models.BooleanField(
        help_text="IDA-catalog only. Show/hide file metadata (file- and folder names, "
        "and other metadata, but not file amounts and sizes).",
        default=None,
        null=True,
        blank=True,
    )

    class Meta(AbstractBaseModel.Meta):
        verbose_name_plural = "Access rights"

    def __str__(self):
        description = self.description
        if isinstance(description, str):
            description = json.loads(description)
        if description:
            return str(next(iter(description.values())))
        elif self.access_type:
            return self.access_type.pref_label.get("en", "access rights")
        else:
            return "Access Rights"

    def _embargo_passed(self, date: date):
        if not self.available:
            return False  # Restrict indefinitely
        return date >= self.available

    def _user_has_rems_entitlement(self, user, dataset: "Dataset") -> bool:
        """Check if user has an active REMS entitlement to the dataset."""
        if not settings.REMS_ENABLED:
            return False
        if not dataset.is_rems_dataset:
            return False
        if not getattr(user, "fairdata_username", None):
            return False
        return bool(REMSService().get_user_entitlements_for_dataset(user, dataset))

    def is_data_available(self, request, dataset: "Dataset"):
        """Check if dataset data should be available to request user.

        Returns:
            bool: True if data should be downloadable by request user.
        """
        if dataset.removed or dataset.deprecated:
            return False

        is_published = dataset.state == dataset.StateChoices.PUBLISHED
        if not is_published:
            return False

        access_type = self.access_type.url
        if access_type == AccessTypeChoices.OPEN:
            return True
        elif access_type == AccessTypeChoices.LOGIN:
            return request.user.is_authenticated
        elif access_type == AccessTypeChoices.EMBARGO:
            return self._embargo_passed(datetime_to_date(timezone.now()))
        elif access_type in {AccessTypeChoices.PERMIT, AccessTypeChoices.RESTRICTED}:
            # Access controlled by REMS. User needs to have at least one active entitlement
            return self._user_has_rems_entitlement(request.user, dataset)
        return False  # unknown or missing access type

    def save(self, *args, **kwargs):
        if self.rems_approval_type == REMSApprovalType.MANUAL:
            raise ValidationError(
                {"rems_approval_type": f"{REMSApprovalType.MANUAL} is not implemented yet"}
            )
        return super().save(*args, **kwargs)
