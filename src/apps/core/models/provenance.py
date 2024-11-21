import uuid

from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.copier import ModelCopier
from apps.common.helpers import ensure_instance_id, prepare_for_copy
from apps.common.models import AbstractBaseModel, AbstractFreeformConcept

from .catalog_record import Dataset, DatasetActor
from .concepts import EventOutcome, LifecycleEvent, PreservationEvent, Spatial


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

    copier = ModelCopier(
        copied_relations=["spatial", "temporal", "is_associated_with", "used_entity", "variables"],
        parent_relations=["dataset"],
        bulk=True,
    )

    title = HStoreField(
        help_text=_('example: {"en":"title", "fi":"otsikko"}'), null=True, blank=True
    )
    description = HStoreField(
        help_text=_('example: {"en":"description", "fi": "kuvaus"}'), null=True, blank=True
    )
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
    preservation_event = models.ForeignKey(
        PreservationEvent, on_delete=models.CASCADE, null=True, blank=True
    )
    event_outcome = models.ForeignKey(
        EventOutcome, on_delete=models.CASCADE, null=True, blank=True
    )
    outcome_description = HStoreField(
        help_text=_('example: {"en":"successfully collected",}'), null=True, blank=True
    )
    is_associated_with = models.ManyToManyField(
        DatasetActor, related_name="provenance", blank=True
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, null=True, blank=True, related_name="provenance"
    )

    @classmethod
    def _create_copy(cls, original, dataset=None):
        copy_actors = original.is_associated_with.all()
        copy = prepare_for_copy(original)

        if dataset:
            ensure_instance_id(dataset)
            copy.dataset = dataset

        if original.spatial:
            new_spatial = Spatial.create_copy(original.spatial, dataset)
            copy.spatial = new_spatial

        copy.save()
        copy.is_associated_with.set(copy_actors)
        return copy, original

    def __str__(self):
        label = self.title or self.description
        if label is not None:
            return str(next(iter(label.items())))
        else:
            return str(self.id)


class VariableUniverse(AbstractFreeformConcept):
    """Indicates the Universe of a represented variable.

    RDF Class: disco:Universe
    Source: [DDI-RDF Discovery Vocabulary](https://rdf-vocabulary.ddialliance.org/discovery.html#dfn-disco-universe)

    E.g. "All the population in the national territory
    at the moment the census is carried out."
    """

    copier = ModelCopier(copied_relations=[], parent_relations=["provenancevariable"])


class VariableConcept(AbstractFreeformConcept):
    """Concept of a variable.

    RDF Class: disco:Concept
    Source: [DDI-RDF Discovery Vocabulary](https://rdf-vocabulary.ddialliance.org/discovery.html#dfn-disco-concept)

    E.g. "Demographic Variables"
    """

    copier = ModelCopier(copied_relations=[], parent_relations=["provenancevariable"])


class ProvenanceVariable(AbstractBaseModel):
    """A variable provides the definition of a column in a rectangular data file.

    RDF Class: disco:Variable
    Source: [DDI-RDF Discovery Vocabulary](https://rdf-vocabulary.ddialliance.org/discovery.html#dfn-disco-variable)
    """

    copier = ModelCopier(copied_relations=["concept", "universe"], parent_relations=["provenance"])

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pref_label = HStoreField(help_text='example: {"en":"Age"}')
    description = HStoreField(
        help_text='example: {"en":"This variable indicates the person\'s age in years"}',
        null=True,
        blank=True,
    )
    concept = models.ForeignKey(VariableConcept, on_delete=models.SET_NULL, null=True, blank=True)
    universe = models.ForeignKey(
        VariableUniverse, on_delete=models.SET_NULL, null=True, blank=True
    )
    representation = models.URLField(
        null=True,
        blank=True,
        help_text="Scheme that contains the possible values of the variable.",
    )
    provenance = models.ForeignKey(
        Provenance, on_delete=models.CASCADE, related_name="variables", null=True, blank=True
    )
