import json
import uuid
from datetime import date

from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.common.copier import ModelCopier
from apps.common.helpers import datetime_to_date
from apps.common.models import AbstractBaseModel
from apps.core.models.concepts import AccessType, DatasetLicense, RestrictionGrounds


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
    copier = ModelCopier(copied_relations=["license"], parent_relations=["datasets", "catalogs"])

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ManyToManyField(
        DatasetLicense,
        related_name="access_rights",
    )
    access_type = models.ForeignKey(
        AccessType, on_delete=models.SET_NULL, related_name="access_rights", null=True
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
    history = HistoricalRecords(m2m_fields=(license,))

    class Meta:
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

    def is_data_available(self, request, dataset):
        """Check if dataset data should be available to request user.

        Returns:
            bool: True if data should be downloadable by request user.
        """
        if dataset.removed or dataset.is_deprecated:
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
        elif access_type == AccessTypeChoices.PERMIT:
            return False  # TODO: REMS
        return False  # access type is "restricted" or missing
