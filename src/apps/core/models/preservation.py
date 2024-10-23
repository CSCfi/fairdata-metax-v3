import uuid

from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _
from simple_history.models import HistoricalRecords
from django.utils import timezone

from apps.common.copier import ModelCopier
from apps.common.models import AbstractBaseModel, AbstractDatasetProperty
from apps.core.models.contract import Contract


class Preservation(AbstractBaseModel):
    """Model describing dataset's preservation status"""

    copier = ModelCopier(copied_relations=[])

    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        related_name="preservation_entries",
        null=True,
        blank=True,
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preservation_identifier = models.CharField(max_length=256, null=True, blank=True)

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

    state = models.IntegerField(
        choices=PreservationState.choices,
        default=PreservationState.NONE,
        help_text=_("Record state in DPRES."),
    )
    state_modified = models.DateTimeField(
        help_text="Last preservation state change",
        blank=True,
        null=True,
    )
    description = HStoreField(
        blank=True,
        null=True,
        help_text=_(
            "Description for the preservation state. This can be an error message "
            "or a human readable summary of the last preservation action.\n\n"
            'Example: {"en": "Packaging failed", "fi": "Paketointi epäonnistui"}'
        ),
    )
    reason_description = models.TextField(
        blank=True,
        null=False,
        default="",
        help_text=_("User-provided reason for rejecting or accepting a dataset in DPRES"),
    )
    dataset_version = models.OneToOneField(
        "self",
        on_delete=models.DO_NOTHING,
        null=True,
        related_name="dataset_origin_version",
        help_text=_("Link between the dataset stored in DPRES and the originating dataset"),
    )

    class Meta(AbstractBaseModel.Meta):
        constraints = [
            # Dataset that enters the preservation process must have a
            # contract
            models.CheckConstraint(
                check=Q(state__lt=0) | Q(contract_id__isnull=False),
                name="%(app_label)s_%(class)s_has_valid_contract",
            )
        ]
