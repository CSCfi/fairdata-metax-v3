from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.models import AbstractBaseModel, AbstractFreeformConcept
from apps.common.helpers import prepare_for_copy, ensure_instance_id

from .catalog_record import Dataset, DatasetActor
from .concepts import EventOutcome, LifecycleEvent, Spatial


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

    title = HStoreField(help_text=_('example: {"en":"title", "fi":"otsikko"}'), null=True)
    description = HStoreField(help_text=_('example: {"en":"description", "fi": "kuvaus"}'))
    spatial = models.OneToOneField(
        Spatial,
        on_delete=models.SET_NULL,
        related_name="provenance",
        null=True,
        blank=True,
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

    @classmethod
    def create_copy(cls, original, dataset=None):
        copy_actors = original.is_associated_with.all()
        copy = prepare_for_copy(original)

        if dataset:
            ensure_instance_id(dataset)
            copy.dataset = dataset

        if original.spatial:
            new_spatial, _ = Spatial.create_copy(original.spatial, dataset)
            copy.spatial = new_spatial

        copy.save()
        copy.is_associated_with.set(copy_actors)
        return copy, original

    def __str__(self):
        if self.title is not None:
            return str(next(iter(self.title.items())))
        else:
            return str(next(iter(self.description.items())))


class ProvenanceVariable(AbstractFreeformConcept):
    provenance = models.ForeignKey(Provenance, on_delete=models.CASCADE, related_name="variables")
