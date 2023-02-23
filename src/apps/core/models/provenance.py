from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.models import AbstractBaseModel, AbstractFreeformConcept

from .catalog_record import Dataset, DatasetActor, Spatial
from .concepts import EventOutcome, LifecycleEvent


class Provenance(AbstractBaseModel):
    """History and events of the dataset

    Attributes:
        title(HStoreField): Title of the event
        description(HStoreField): Description of the event
        spatial(Spatial): Spatial ForeignKey relation
        lifecycle_event(LifecycleEvent): LifecycleEvent ForeignKey relation
        event_outcome(EventOutcome): EventOutcome ForeignKey relation
        outcome_description(HStoreField)
        is_associated_with(models.ManyToManyField): actors associated with the event
        dataset(Dataset): Dataset ForeignKey relation
    """

    title = HStoreField(help_text=_('example: {"en":"title", "fi":"otsikko"}'))
    description = HStoreField(help_text=_('example: {"en":"description", "fi": "kuvaus"}'))
    # Making foreign-key unique same as OneToOneField
    spatial = models.ForeignKey(
        Spatial, on_delete=models.CASCADE, null=True, blank=True, unique=True
    )
    lifecycle_event = models.ForeignKey(
        LifecycleEvent, on_delete=models.CASCADE, null=True, blank=True
    )
    event_outcome = models.ForeignKey(
        EventOutcome, on_delete=models.CASCADE, null=True, blank=True
    )
    outcome_description = HStoreField(
        help_text=_('example: {"en":"successfully collected",}'), null=True, blank=True
    )
    is_associated_with = models.ManyToManyField(DatasetActor, related_name="provenance")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="provenance")


class ProvenanceVariable(AbstractFreeformConcept):
    provenance = models.ForeignKey(Provenance, on_delete=models.CASCADE, related_name="variables")
