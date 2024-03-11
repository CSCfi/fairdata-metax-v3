import logging
from typing import Dict

from django.utils.translation import gettext_lazy as _

from apps.actors.models import Person
from apps.common.serializers.serializers import CommonListSerializer
from apps.common.serializers.validators import AllOf
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.serializers.dataset_actor_serializers.member_serializer import (
    DatasetMemberContext,
    DatasetMemberSerializer,
    IntegerOrTagField,
)

logger = logging.getLogger(__name__)


class DatasetPersonSerializer(DatasetMemberSerializer):
    """Serializer for dataset person.

    Same person can be multiple times in the same dataset."""

    id = IntegerOrTagField(required=False)
    save_validator = AllOf(["name"])

    def get_dataset_persons(self, dataset) -> Dict[str, DatasetMemberContext]:
        """Get DatasetMemberContext for all persons in dataset."""
        persons = {}

        def add_person(person):
            if person:
                persons[str(person.id)] = DatasetMemberContext(
                    object=person, is_existing=True, existing_data=self.get_existing_data(person)
                )

        for actor in dataset.actors.all():
            add_person(actor.person)

        for provenance in dataset.provenance.all():
            for actor in provenance.is_associated_with.all():
                add_person(actor.person)

        return persons

    def get_dataset_members(self) -> Dict[str, DatasetMemberContext]:
        if "dataset_persons" not in self.context:
            dataset: Dataset = self.context.get("dataset")
            if dataset:
                self.context["dataset_persons"] = self.get_dataset_persons(dataset)
            else:
                self.context["dataset_persons"] = {}
        return self.context["dataset_persons"]

    class Meta:
        model = Person
        fields = ("id", "name", "email", "external_identifier")
        extra_kwargs = {"name": {"required": False}}  # checked by save_validator
        list_serializer_class = CommonListSerializer
