import logging
from datetime import datetime
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.common.helpers import date_to_datetime, omit_empty, omit_none, single_translation
from apps.refdata.models import AbstractConcept

logger = logging.getLogger(__name__)


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
        deprecated (datetime): Indicates when dataset was deprecated
        preservation_state (int): Long term preservation state of the dataset
        state (str): State of the dataset, can be draft or published
        cumulative_state (int): Cumulative state of the dataset
        created (datetime): Datetime when the dataset was created
        removed (datetime): Indicates when dataset was removed
        metadata_owner (object): Object must be compatible with MetadataProvider model attributes
        title (dict): Dataset title in form of {"fi": "otsikko", "en": "title"}
        description (dict): Dataset description in form of {"fi": "kuvaus", "en": "description"}
        modified (datetime): Datetime when the dataset was last modified
        persistent_identifier (str): Persistent identifier of the dataset
        keyword (str): Keyword of the dataset
        theme (Queryset): The main category of the dataset
        relation (Queryset): Relation to another entity.
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
    theme: QuerySet
    deprecated: datetime
    preservation_state: int
    relation: QuerySet
    state: str
    cumulative_state: int
    created: datetime
    removed: datetime
    metadata_owner: object
    title: dict
    description: dict
    bibliographic_citation: Optional[str]
    modified: datetime
    persistent_identifier: str
    keyword: str
    data_catalog: object
    cumulation_started: datetime
    cumulation_ended: datetime
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
        omit_scheme=False,
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
            if row.in_scheme and not omit_scheme:
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
            obj["alt"] = str(altitude_in_meters)
        as_wkt = []
        if model_obj.custom_wkt:
            custom_wkt = model_obj.custom_wkt
            as_wkt.extend(custom_wkt)
        elif model_obj.reference:
            if ref_wkt := model_obj.reference.as_wkt:
                as_wkt.append(ref_wkt)
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

    def _convert_v3_temporal_to_v2(self, temporal):
        """Convert single temporal object to v2."""
        v2_temporal = {}
        if temporal.start_date:
            v2_temporal["start_date"] = date_to_datetime(temporal.start_date).isoformat()
        if temporal.end_date:
            v2_temporal["end_date"] = date_to_datetime(temporal.end_date).isoformat()
        if temporal.temporal_coverage:
            v2_temporal["temporal_coverage"] = temporal.temporal_coverage
        return v2_temporal

    def _generate_v2_temporal(self, document: Dict):
        obj_list = []
        for temporal in self.temporal.filter(provenance=None):
            obj_list.append(self._convert_v3_temporal_to_v2(temporal))
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

    def _construct_v2_refdata_object(self, concept: AbstractConcept, omit_fields=[]):
        if not concept:
            return None
        obj = {
            "pref_label": concept.pref_label,
            "in_scheme": concept.in_scheme,
            "identifier": concept.url,
        }
        for field in omit_fields:
            obj.pop(field, None)
        return obj

    def _construct_v2_relation(self, relation):
        entity = relation.entity
        return {
            "relation_type": self._construct_v2_refdata_object(
                relation.relation_type, omit_fields=["in_scheme"]  # no relation type scheme in v2
            ),
            "entity": {
                "title": entity.title or None,
                "description": entity.description or None,
                "identifier": entity.entity_identifier or None,
                "type": self._construct_v2_refdata_object(entity.type),
            },
        }

    def _generate_v2_relation(self, document: Dict):
        obj_list = []
        for relation in self.relation.all():
            obj = self._construct_v2_relation(relation)
            obj_list.append(obj)
        if len(obj_list) != 0:
            document["research_dataset"]["relation"] = obj_list
        return obj_list

    def _construct_v2_concept(self, concept) -> Optional[Dict]:
        if not concept:
            return None
        return omit_none(
            {
                "pref_label": concept.pref_label,
                "definition": concept.definition,
                "identifier": concept.concept_identifier,
                "in_scheme": concept.in_scheme,
            }
        )

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
                data["temporal"] = self._convert_v3_temporal_to_v2(provenance.temporal)

            if variables := provenance.variables.all():
                data["variable"] = [
                    omit_none(
                        {
                            "pref_label": variable.pref_label,
                            "description": variable.description,
                            "concept": self._construct_v2_concept(variable.concept),
                            "universe": self._construct_v2_concept(variable.universe),
                            "representation": variable.representation,
                        }
                    )
                    for variable in variables
                ]
            if provenance.preservation_event:
                data["preservation_event"] = {
                    "pref_label": provenance.preservation_event.pref_label,
                    "identifier": provenance.preservation_event.url,
                    "in_scheme": provenance.preservation_event.in_scheme,
                }
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

            obj_list.append(omit_none(data))
        if len(obj_list) != 0:
            document["research_dataset"]["provenance"] = obj_list
        return obj_list

    def _generate_v2_access_rights(self) -> Optional[Dict]:
        if not self.access_rights:
            return None
        data = {
            "access_type": {
                "in_scheme": self.access_rights.access_type.in_scheme,
                "identifier": self.access_rights.access_type.url,
                "pref_label": self.access_rights.access_type.pref_label,
            },
            "license": [],
        }

        if available := getattr(self.access_rights, "available", None):
            data["available"] = available.isoformat()

        if description := self.access_rights.description:
            data["description"] = description

        for license in self.access_rights.license.all():
            row = {
                "identifier": license.reference.url,
                "title": license.title or license.reference.pref_label,
                "description": license.description,
            }
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

    def generate_org(self, org, contributor_type=None):
        v2_org = {
            "@type": "Organization",
            "name": org.pref_label,
            "identifier": org.url or org.external_identifier,
        }

        if org.parent:
            v2_org["is_part_of"] = self.generate_org(org.parent)

        if contributor_type:
            v2_org["contributor_type"] = contributor_type

        return v2_org

    def _add_funder_type(self, project, funder_type):
        if funder_type:
            project["funder_type"] = {
                "pref_label": funder_type.pref_label,
                "identifier": funder_type.url,
                "in_scheme": funder_type.in_scheme,
            }

    def _add_funder_organization(self, project, funder_organization):
        if funder_organization:
            if "has_funding_agency" not in project:
                project["has_funding_agency"] = []
            project["has_funding_agency"].append(self.generate_org(funder_organization))

    def _add_funder_identifier(self, project, funder_identifier):
        if funder_identifier:
            project["has_funder_identifier"] = funder_identifier

    def _add_funder_source_organizations(self, project, participating_organizations):
        for participating_organization in participating_organizations:
            if "source_organization" not in project:
                project["source_organization"] = []
            project["source_organization"].append(self.generate_org(participating_organization))

    def _generate_v2_dataset_projects(self) -> List:
        obj_list = []
        for dataset_project in self.projects.all():
            project = {
                "name": dataset_project.title,
                "identifier": dataset_project.project_identifier,
                "has_funding_agency": [],
                "source_organization": [],
            }

            funder_type = None
            funder_organization = None
            funder_identifier = None

            for fund in dataset_project.funding.all():
                if funder := fund.funder:
                    funder_type = funder.funder_type
                    funder_organization = funder.organization
                    self._add_funder_type(project, funder_type)
                    self._add_funder_organization(project, funder_organization)
                funder_identifier = fund.funding_identifier
                self._add_funder_identifier(project, funder_identifier)

            self._add_funder_source_organizations(
                project,
                participating_organizations=dataset_project.participating_organizations.all(),
            )

            obj_list.append(project)
        return obj_list

    def _construct_v2_removed_field(self):
        if self.removed:
            return True
        else:
            return False

    def _construct_v2_checksum(self, checksum: str) -> Optional[dict]:
        if not checksum:
            return None

        try:
            algo, value = checksum.split(":", maxsplit=1)
        except ValueError:
            algo = None
            value = checksum

        v2_algos = {
            "md5": "MD5",
            "sha1": "SHA-1",
            "sha224": "SHA-224",
            "sha256": "SHA-384",
            "sha512": "SHA-512",
        }
        v2_algo = v2_algos.get(algo, "OTHER")
        return {
            "checksum_value": value,
            "algorithm": v2_algo,
        }

    def _construct_v2_remote_resource(self, remote_resource) -> dict:
        access_url = None
        if url := remote_resource.access_url:
            access_url = {"identifier": url}
        download_url = None
        if url := remote_resource.download_url:
            download_url = {"identifier": url}

        return omit_none(
            {
                "title": single_translation(remote_resource.title),
                "description": single_translation(remote_resource.description),
                "checksum": self._construct_v2_checksum(remote_resource.checksum),
                "mediatype": remote_resource.mediatype,
                "use_category": self._construct_v2_refdata_object(remote_resource.use_category),
                "file_type": self._construct_v2_refdata_object(remote_resource.file_type),
                "access_url": access_url,
                "download_url": download_url,
            }
        )

    def _generate_v2_remote_resources(self, document) -> List:
        obj_list = [
            self._construct_v2_remote_resource(resource)
            for resource in self.remote_resources.all()
        ]
        if obj_list:
            document["research_dataset"]["remote_resources"] = obj_list
        return obj_list

    def add_actor(self, role: str, document: Dict):
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

    def as_v2_dataset(self) -> Dict:
        research_dataset = {
            "title": self.title,
            "description": self.description,
            "modified": self.modified.isoformat(),
            "preferred_identifier": self.persistent_identifier,
            "keyword": self.keyword,
            "access_rights": self._generate_v2_access_rights() if self.access_rights else None,
            "is_output_of": self._generate_v2_dataset_projects(),
            "bibliographic_citation": self.bibliographic_citation,
        }

        if file_set := getattr(self, "file_set", None):
            research_dataset["total_files_byte_size"] = file_set.total_files_size
        if self.issued:
            research_dataset["issued"] = self.issued.isoformat()
        doc = {
            "identifier": str(self.id),
            "api_meta": {"version": self.api_version},
            "deprecated": self.deprecated is not None,
            "state": self.state,
            "cumulative_state": self.cumulative_state.real,
            "date_created": self.created.isoformat(),
            "removed": self._construct_v2_removed_field(),
            "research_dataset": research_dataset,
        }
        if self.deprecated:
            doc["date_deprecated"] = self.deprecated.isoformat()
        if self.metadata_owner:
            if hasattr(self.metadata_owner, "user"):
                doc["metadata_provider_user"] = self.metadata_owner.user.username
            else:
                doc["metadata_provider_user"] = "None"
            if hasattr(self.metadata_owner, "organization"):
                doc["metadata_provider_org"] = self.metadata_owner.organization
                doc["metadata_owner_org"] = self.metadata_owner.organization
            else:
                doc["metadata_provider_org"] = "None"
                doc["metadata_owner_org"] = "None"

        if self.data_catalog:
            doc["data_catalog"] = {"identifier": self.data_catalog.id}
        if self.preservation:
            doc["preservation_state"] = self.preservation.state
            doc["preservation_identifier"] = self.preservation.id
        if self.cumulation_started:
            doc["date_cumulation_started"] = self.cumulation_started.isoformat()
        if self.cumulation_ended:
            doc["date_cumulation_ended"] = self.cumulation_ended.isoformat()
        if self.last_cumulative_addition:
            doc["date_last_cumulative_addition"] = self.last_cumulative_addition.isoformat()
        if self.last_modified_by:
            doc["user_modified"] = self.last_modified_by.username

        self._generate_v2_other_identifiers(doc)
        self._generate_v2_ref_data_field(
            "language", doc, pref_label_text="title", omit_scheme=True
        )
        self._generate_v2_ref_data_field("field_of_science", doc)
        self._generate_v2_ref_data_field("infrastructure", doc)
        self._generate_v2_ref_data_field("theme", doc)
        self._generate_v2_spatial(doc)
        self._generate_v2_temporal(doc)
        self._generate_v2_provenance(doc)
        self._generate_v2_relation(doc)
        self._generate_v2_remote_resources(doc)

        for role in ["creator", "publisher", "curator", "contributor", "rights_holder"]:
            self.add_actor(role, doc)

        # Remove empty values from research_dataset
        doc["research_dataset"] = omit_empty(research_dataset, recurse=True)
        return doc
