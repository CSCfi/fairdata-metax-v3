import logging
from datetime import datetime
from typing import Dict, List

from django.contrib.auth import get_user_model
from django.core.validators import EMPTY_VALUES
from django.db.models import QuerySet

from apps.common.views import CommonModelViewSet
from apps.core.permissions import DatasetNestedAccessPolicy

logger = logging.getLogger(__name__)


class DatasetNestedViewSetMixin(CommonModelViewSet):
    access_policy = DatasetNestedAccessPolicy

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return self.serializer_class.Meta.model.available_objects.none()
        return self.serializer_class.Meta.model.available_objects.filter(
            dataset=self.kwargs["dataset_pk"]
        )

    def perform_create(self, serializer):
        return serializer.save(dataset_id=self.kwargs["dataset_pk"])

    def get_dataset_pk(self):
        context = super().get_serializer_context()
        return self.kwargs.get("dataset_pk") or context.get("dataset_pk")

    def get_dataset_instance(self):
        from .models import Dataset

        return Dataset.objects.get(id=self.get_dataset_pk())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dataset_pk"] = self.kwargs.get("dataset_pk")
        return context


class V2DatasetMixin:
    """Mixin for converting the class object into v2 Dataset

    Attributes:
        temporal (QuerySet): Set members must have `end_date` and `start_date` attributes
        other_identifiers (QuerySet): Set members must have
            `notation` and `identifier_type` attributes.
            `identifier_type` must have reference-data compatible attributes.
        spatial (QuerySet): Set members must have
            `geographic_name`, `reference`, `full_address`, `altitude_in_meters`
            and `custom_wkt` attributes.
            `reference` must have `refdata.Location` compatible attributes.
        provenance (QuerySet): Set members must have `title`, `description`,
            `spatial`, `variable`, `lifecycle_event`, `event_outcome`,
            `outcome_description` and `is_associated_with` attributes.
            `spatial` must have `refdata.Location` compatible attributes.
            `variable`, `lifecycle_event`, `event_outcome` and `outcome_description`
            must have reference-data compatible attributes.
            `is_associated_with` Set members must have `person` and `organization` attributes.
        access_rights (object): Object must be compatible with AccessRights model attributes
        is_output_of (QuerySet): Set members must have DatasetProject compatible attributes.
        actors (QuerySet): Set members must have DatasetActor compatible attributes.
        is_deprecated (bool): Indicates if dataset is deprecated
        preservation_state (int): Long term preservation state of the dataset
        state (str): State of the dataset, can be draft or published
        cumulative_state (int): Cumulative state of the dataset
        created (datetime): Datetime when the dataset was created
        is_removed (bool): Indicates if dataset is removed
        metadata_owner (object): Object must be compatible with MetadataProvider model attributes
        title (dict): Dataset title in form of {"fi": "otsikko", "en": "title"}
        description (dict): Dataset description in form of {"fi": "kuvaus", "en": "description"}
        modified (datetime): Datetime when the dataset was last modified
        persistent_identifier (str): Persistent identifier of the dataset
        keyword (str): Keyword of the dataset
        data_catalog (object): Object must be compatible with DataCatalog model attributes
        cumulation_started (datetime): Datetime when the dataset started accumulation process
        last_cumulative_addition (datetime): Datetime when the dataset had last cumulative event
        preservation_identifier (str): Preservation identifier of the dataset
        last_modified_by (object): Object must be compatible with User model attributes
        issued (datetime): Datetime when the dataset was issued
    """

    # Cant use the real types because of circular imports
    temporal: QuerySet
    other_identifiers: QuerySet
    spatial: QuerySet
    provenance: QuerySet
    access_rights: object
    is_output_of: QuerySet
    actors: QuerySet
    is_deprecated: bool
    preservation_state: int
    state: str
    cumulative_state: int
    created: datetime
    is_removed: bool
    metadata_owner: object
    title: dict
    description: dict
    modified: datetime
    persistent_identifier: str
    keyword: str
    data_catalog: object
    cumulation_started: datetime
    last_cumulative_addition: datetime
    preservation_identifier: str
    last_modified_by: get_user_model()
    issued: datetime

    def _generate_v2_ref_data_field(
        self,
        field_name: str,
        document: Dict,
        pref_label_text: str = "pref_label",
        top_level_key_name: str = None,
        extra_top_level_fields: List = None,
    ):
        """

        Args:
            field_name (RelatedManager): ForeignKey from which
                the reference data object is constructed
            document (Dict): V2 Dataset dictionary
            pref_label_text (): Object reference data key name
            top_level_key_name ():
            extra_top_level_fields ():

        Returns:

        """

        related_manager = getattr(self, field_name)
        if related_manager.count() == 0:
            return

        obj_list = []
        for row in related_manager.all():
            obj = {pref_label_text: row.pref_label, "identifier": row.url}
            if row.in_scheme:
                obj["in_scheme"] = row.in_scheme
            if top_level_key_name:
                obj = {top_level_key_name: obj}
                obj_list.append(obj)
            else:
                obj_list.append(obj)
            if extra_top_level_fields:
                for field in extra_top_level_fields:
                    if getattr(row, field) is not None:
                        value = getattr(row, field)
                        logger.info(f"{value=}")
                        obj.update({field: value})
        if len(obj_list) != 0:
            document["research_dataset"][field_name] = obj_list
        return obj_list

    def _construct_v2_spatial(self, model_obj):
        obj = {"geographic_name": model_obj.geographic_name}
        if model_obj.reference:
            place_uri_obj = {}
            if in_scheme := model_obj.reference.in_scheme:
                place_uri_obj["in_scheme"] = in_scheme
            if identifier := model_obj.reference.url:
                place_uri_obj["identifier"] = identifier
            if pref_label := model_obj.reference.pref_label:
                place_uri_obj["pref_label"] = pref_label
            obj["place_uri"] = place_uri_obj
        if full_address := model_obj.full_address:
            obj["full_address"] = full_address
        if altitude_in_meters := model_obj.altitude_in_meters:
            obj["altitude_in_meters"] = altitude_in_meters
        as_wkt = []
        if model_obj.reference:
            if ref_wkt := model_obj.reference.as_wkt:
                as_wkt.append(ref_wkt)
        if model_obj.custom_wkt:
            custom_wkt = model_obj.custom_wkt or []
            as_wkt = as_wkt + [*custom_wkt]
        if len(as_wkt) > 0:
            obj["as_wkt"] = [v for v in as_wkt if v is not None]
        return obj

    def _generate_v2_other_identifiers(self, document: Dict):
        obj_list = []
        for identifier in self.other_identifiers.all():
            obj = {"notation": identifier.notation}
            if identifier.identifier_type:
                obj["type"] = {
                    "in_scheme": identifier.identifier_type.in_scheme,
                    "identifier": identifier.identifier_type.url,
                    "pref_label": identifier.identifier_type.pref_label,
                }
            obj_list.append(obj)
        if len(obj_list) != 0:
            document["research_dataset"]["other_identifier"] = obj_list
        return obj_list

    def _generate_v2_temporal(self, document: Dict):
        obj_list = []
        for temporal in self.temporal.filter(provenance=None):
            obj_list.append(
                {
                    "start_date": temporal.start_date,
                    "end_date": temporal.end_date,
                }
            )
        if len(obj_list) != 0:
            document["research_dataset"]["temporal"] = obj_list
        return obj_list

    def _generate_v2_spatial(self, document: Dict):
        obj_list = []
        for spatial in self.spatial.all():
            obj = self._construct_v2_spatial(spatial)
            obj_list.append(obj)
        if len(obj_list) != 0:
            document["research_dataset"]["spatial"] = obj_list
        return obj_list

    def _generate_v2_provenance(self, document: Dict) -> List:
        obj_list = []
        for provenance in self.provenance.all():
            data = {
                "title": provenance.title,
                "description": provenance.description,
            }

            if provenance.spatial:
                data["spatial"] = self._construct_v2_spatial(provenance.spatial)

            if hasattr(provenance, "temporal"):
                data["temporal"] = {
                    "start_date": provenance.temporal.start_date,
                    "end_date": provenance.temporal.end_date,
                }
            if provenance.variables.all().count() != 0:
                data["variable"] = []
                for variable in provenance.variables.all():
                    var_data = {"pref_label": variable.pref_label}
                    data["variable"].append(var_data)
            if provenance.lifecycle_event:
                data["lifecycle_event"] = {
                    "pref_label": provenance.lifecycle_event.pref_label,
                    "identifier": provenance.lifecycle_event.url,
                    "in_scheme": provenance.lifecycle_event.in_scheme,
                }
            if provenance.event_outcome:
                data["event_outcome"] = {
                    "pref_label": provenance.event_outcome.pref_label,
                    "identifier": provenance.event_outcome.url,
                    "in_scheme": provenance.event_outcome.in_scheme,
                }
            if provenance.outcome_description:
                data["outcome_description"] = provenance.outcome_description

            if provenance.is_associated_with.all().count() != 0:
                data["was_associated_with"] = []
                for association in provenance.is_associated_with.all():
                    data["was_associated_with"].append(association.as_v2_data())

            obj_list.append(data)
        if len(obj_list) != 0:
            document["research_dataset"]["provenance"] = obj_list
        return obj_list

    def _generate_v2_access_rights(self) -> Dict:
        data = {
            "access_type": {
                "in_scheme": self.access_rights.access_type.in_scheme,
                "identifier": self.access_rights.access_type.url,
                "pref_label": self.access_rights.access_type.pref_label,
            },
            "license": [],
        }

        for license in self.access_rights.license.all():
            row = {
                "identifier": license.reference.url,
                "title": license.reference.pref_label,
            }
            if description := license.description:
                row["description"] = description
            if custom_url := license.custom_url:
                row["license"] = custom_url
            data["license"].append(row)
        for res_grounds in self.access_rights.restriction_grounds.all():
            if not data.get("restriction_grounds"):
                data["restriction_grounds"] = []
            data["restriction_grounds"].append(
                {
                    "identifier": res_grounds.url,
                    "pref_label": res_grounds.pref_label,
                    "in_scheme": res_grounds.in_scheme,
                }
            )
        return data

    def _generate_v2_dataset_project(self) -> List:
        from apps.core.models import ProjectContributor

        def _populate_participant(participant: ProjectContributor):
            participant_type = "Organization" if participant.actor.person is None else "Person"
            _contribution_types = []
            for cont_type in participant.contribution_type.all():
                _contribution_types.append(
                    {
                        "pref_label": cont_type.pref_label,
                        "identifier": cont_type.url,
                        "in_scheme": cont_type.in_scheme,
                    }
                )
            if participant_type == "Person":
                person_name = None
                if participant.actor.person:
                    person_name = participant.actor.person.name
                _source_organization = {
                    "name": person_name,
                    "@type": participant_type,
                }
                if _contribution_types not in EMPTY_VALUES:
                    _source_organization["contributor_type"] = _contribution_types
                if participant.participating_organization not in EMPTY_VALUES:
                    _source_organization["member_of"] = {
                        "name": participant.participating_organization.pref_label,
                        "@type": "Organization",
                        "identifier": participant.participating_organization.url,
                    }
            else:
                _source_organization = {
                    "name": participant.participating_organization.pref_label,
                    "@type": participant_type,
                    "identifier": participant.participating_organization.url,
                }
                if _contribution_types not in EMPTY_VALUES:
                    _source_organization["contributor_type"] = _contribution_types
            return _source_organization

        obj_list = []
        for dataset_project in self.is_output_of.all():
            project = {
                "name": dataset_project.name,
                "identifier": dataset_project.project_identifier,
                "has_funder_identifier": dataset_project.funder_identifier,
                "funder_type": {},
                "has_funding_agency": [],
                "source_organization": [],
            }
            if funder_type := dataset_project.funder_type:
                project["funder_type"] = {
                    "pref_label": funder_type.pref_label,
                    "identifier": funder_type.url,
                    "in_scheme": funder_type.in_scheme,
                }
            for funder_agency in dataset_project.funding_agency.all():
                if "has_funding_agency" not in project:
                    project["has_funding_agency"] = []
                project["has_funding_agency"].append(_populate_participant(funder_agency))

            for participating_organization in dataset_project.participating_organization.all():
                if "source_organization" not in project:
                    project["source_organization"] = []
                project["source_organization"].append(
                    _populate_participant(participating_organization)
                )

            obj_list.append(project)
        return obj_list

    def as_v2_dataset(self) -> Dict:
        def add_actor(role: str, document: Dict):
            actors = self.actors.filter(roles__contains=[role])
            if actors.count() == 0:
                return
            if role != "publisher":
                document["research_dataset"][role] = []
            for dataset_actor in actors:
                data = dataset_actor.as_v2_data()
                if role == "publisher":
                    document["research_dataset"][role] = data
                else:
                    document["research_dataset"][role].append(data)

        total_files_byte_size = 0
        if file_set := getattr(self, "file_set", None):
            total_files_byte_size = file_set.total_files_size

        doc = {
            "identifier": str(self.id),
            "deprecated": self.is_deprecated,
            "preservation_state": self.preservation_state,
            "state": self.state,
            "cumulative_state": self.cumulative_state.real,
            "date_created": self.created,
            "removed": self.is_removed,
            "metadata_provider_user": self.metadata_owner.user.username,
            "metadata_provider_org": self.metadata_owner.organization,
            "metadata_owner_org": self.metadata_owner.organization,
            "research_dataset": {
                "title": self.title,
                "description": self.description,
                "modified": self.modified,
                "preferred_identifier": self.persistent_identifier,
                "total_files_byte_size": total_files_byte_size,
                "keyword": self.keyword,
                "access_rights": self._generate_v2_access_rights(),
            },
            "data_catalog": {"identifier": self.data_catalog.id},
        }
        if self.cumulation_started:
            doc["date_cumulation_started"] = self.cumulation_started
        if self.last_cumulative_addition:
            doc["date_last_cumulative_addition"] = self.last_cumulative_addition
        if self.preservation_identifier:
            doc["preservation_identifier"] = self.preservation_identifier
        if self.last_modified_by:
            doc["user_modified"] = self.last_modified_by.username
        if self.issued:
            doc["research_dataset"]["issued"] = self.issued
        if project := self._generate_v2_dataset_project():
            doc["research_dataset"]["is_output_of"] = project

        self._generate_v2_other_identifiers(doc)
        self._generate_v2_ref_data_field("language", doc, pref_label_text="title")
        self._generate_v2_ref_data_field("field_of_science", doc)
        self._generate_v2_ref_data_field("infrastructure", doc)
        self._generate_v2_spatial(doc)
        self._generate_v2_temporal(doc)
        self._generate_v2_provenance(doc)
        add_actor("creator", doc)
        add_actor("publisher", doc)
        # logger.info(f"{doc=}")
        return doc
