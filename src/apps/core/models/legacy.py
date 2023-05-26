import json
import logging
from collections import namedtuple
from pprint import pprint
from typing import Dict, List

from deepdiff import DeepDiff
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.dateparse import parse_datetime

from apps.actors.models import Actor, Organization
from apps.common.helpers import parse_iso_dates_in_nested_dict
from apps.files.models import File, FileStorage
from apps.files.serializers.file_serializer import get_or_create_file_storage
from apps.refdata.models import FunderType, License, Location
from apps.users.models import MetaxUser

from .catalog_record import (
    Dataset,
    DatasetActor,
    DatasetProject,
    MetadataProvider,
    OtherIdentifier,
    Temporal,
)
from .concepts import (
    AccessType,
    DatasetLicense,
    EventOutcome,
    FieldOfScience,
    IdentifierType,
    Language,
    LifecycleEvent,
    Spatial,
)
from .contract import Contract
from .data_catalog import AccessRights, AccessRightsRestrictionGrounds, DataCatalog
from .provenance import Provenance, ProvenanceVariable

logger = logging.getLogger(__name__)

PreparedInstances = namedtuple(
    "PreparedInstances", "access_rights, data_catalog, contract, metadata_owner"
)
PostProcessedInstances = namedtuple(
    "PostProcessedInstances",
    "languages, spatial, creators, files, temporal, other_identifiers, field_of_science, provenance, publisher, projects",
)


class LegacyDataset(Dataset):
    """Migrated V1 and V2 Datasets

    Stores legacy dataset json fields and derives v3 dataset fields from them using signals.

    Attributes:
        dataset_json (models.JSONField): V1/V2 dataset json from legacy metax dataset API
        contract_json (models.JSONField): Contract json for which the dataset is under
        files_json (models.JSONField): Files attached to the dataset trough dataset/files API in v2
    """

    dataset_json = models.JSONField()
    contract_json = models.JSONField(null=True, blank=True)
    files_json = models.JSONField(null=True, blank=True)

    @property
    def legacy_identifier(self):
        """Legacy database primary key"""
        return self.dataset_json["identifier"]

    @property
    def legacy_persistent_identifier(self):
        """Resolvable persistent identifier like DOI or URN"""
        return self.legacy_research_dataset.get("preferred_identifier")

    @property
    def metadata_provider_user(self):
        return self.dataset_json["metadata_provider_user"]

    @property
    def metadata_provider_org(self):
        if org := self.dataset_json.get("metadata_provider_org"):
            return org
        else:
            return self.dataset_json["metadata_owner_org"]

    @property
    def legacy_research_dataset(self):
        return self.dataset_json["research_dataset"]

    @property
    def legacy_access_rights(self):
        return self.legacy_research_dataset["access_rights"]

    @property
    def legacy_access_type(self):
        return self.legacy_access_rights["access_type"]

    @property
    def legacy_license(self):
        return self.legacy_access_rights["license"]

    @property
    def legacy_data_catalog(self):
        return self.dataset_json["data_catalog"]

    @property
    def legacy_languages(self):
        return self.legacy_research_dataset["language"]

    @property
    def legacy_field_of_science(self):
        return self.legacy_research_dataset["field_of_science"]

    @property
    def legacy_spatial(self):
        return self._flatten_nested_ref_data_object(
            "spatial", "place_uri", additional_keys=["full_address", "geographic_name", "as_wkt"]
        )

    @property
    def legacy_other_identifiers(self):
        other_ids = self._flatten_nested_ref_data_object(
            "other_identifier", "type", additional_keys=["notation"]
        )
        return other_ids

    @property
    def legacy_contract(self):
        if self.contract_json:
            return self.contract_json["contract_json"]

    def _flatten_nested_ref_data_object(
        self, ref_data_name: str, top_level_key_name: str, additional_keys: List = None
    ) -> List[Dict]:
        """Removes top-level object name-field from json structure.

        Examples:
             {obj: { field: value } becomes { field: value }

        Args:
            ref_data_name (str):
            top_level_key_name (str):
            additional_keys (List): additional fields to put on the root level of the object

        Returns:

        """
        if ref_data := self.legacy_research_dataset.get(ref_data_name):
            obj_list = []
            for obj in ref_data:
                flatten_obj = {**obj[top_level_key_name]}
                if additional_keys:
                    for key in additional_keys:
                        flatten_obj[key] = obj.get(key)
                obj_list.append(flatten_obj)
            return obj_list

    @classmethod
    def parse_temporal_timestamps(cls, legacy_temporal):
        start_date = parse_datetime(legacy_temporal["start_date"])
        end_date = parse_datetime(legacy_temporal["end_date"])
        return start_date, end_date

    def convert_root_level_fields(self):
        """
        Convert catalog_record top level fields to new Dataset format
        Returns:

        """
        self.is_deprecated = self.dataset_json["deprecated"]
        self.cumulation_started = self.dataset_json.get("date_cumulation_started")
        self.cumulation_ended = self.dataset_json.get("date_cumulation_ended")
        self.last_cumulative_addition = self.dataset_json.get("date_last_cumulative_addition")
        self.cumulative_state = self.dataset_json.get("cumulative_state")
        self.previous = self.dataset_json.get("previous_dataset_version")
        self.created = self.dataset_json.get("date_created")

        if modified := self.legacy_research_dataset.get("modified"):
            self.modified = modified
        elif modified := self.dataset_json.get("date_modified"):
            self.modified = modified
        else:
            self.modified = self.created

        if user_modified := self.dataset_json.get("user_modified"):
            user, created = get_user_model().objects.get_or_create(username=user_modified)
            self.last_modified_by = user

        self.preservation_state = self.dataset_json["preservation_state"]
        self.preservation_identifier = self.dataset_json.get("preservation_identifier")
        self.state = self.dataset_json["state"]

    def convert_research_dataset_fields(self):
        """Convert simple research_dataset fields to v3 model

        Returns:

        """
        self.title = self.legacy_research_dataset["title"]
        self.persistent_identifier = self.legacy_persistent_identifier
        self.release_date = self.legacy_research_dataset.get("issued")
        self.description = self.legacy_research_dataset["description"]

        if issued := self.legacy_research_dataset.get("issued"):
            self.issued = issued

        if "keyword" in self.legacy_research_dataset:
            self.keyword = self.legacy_research_dataset["keyword"]

    def attach_access_rights(self) -> AccessRights:
        description = self.legacy_access_rights.get("description", None)

        # access-type object
        access_type, at_created = AccessType.objects.get_or_create(
            url=self.legacy_access_type["identifier"],
            defaults={
                "url": self.legacy_access_type["identifier"],
                "in_scheme": self.legacy_access_type["in_scheme"],
                "pref_label": self.legacy_access_type["pref_label"],
            },
        )

        access_rights = AccessRights(
            access_type=access_type,
            description=description,
        )
        access_rights.save()

        # license objects
        licenses_list = self.legacy_license
        license_objects = []
        for lic in licenses_list:
            url = lic["identifier"]
            lic_ref = License.objects.get(url=url)
            custom_url = lic.get("license", None)
            license_instance, created = DatasetLicense.objects.get_or_create(
                access_rights__datasets=self.id,
                reference=lic_ref,
                defaults={
                    "description": lic.get("description"),
                    "custom_url": custom_url,
                },
            )
            license_objects.append(license_instance)

        for res_grounds in self.legacy_access_rights.get("restriction_grounds", []):
            rg, rg_created = AccessRightsRestrictionGrounds.objects.get_or_create(
                url=res_grounds["identifier"],
                pref_label=res_grounds["pref_label"],
                in_scheme=res_grounds["in_scheme"],
                access_rights=access_rights,
            )
            logger.info(f"restriction_grounds={rg}, created={rg_created}")
        self.access_rights = access_rights
        self.access_rights.license.set(license_objects)
        return access_rights

    def attach_data_catalog(self) -> DataCatalog:
        if hasattr(self, "data_catalog"):
            return self.data_catalog
        catalog_id = self.legacy_data_catalog["identifier"]
        catalog, created = DataCatalog.objects.get_or_create(
            id=catalog_id, defaults={"id": catalog_id, "title": {"und": catalog_id}}
        )
        self.data_catalog = catalog
        return catalog

    def attach_metadata_owner(self) -> Actor:
        """Creates new Actor-object from metadata-owner field, that is usually CSC-username"""
        metadata_user, user_created = MetaxUser.objects.get_or_create(
            username=self.metadata_provider_user
        )
        metadata_owner, owner_created = MetadataProvider.objects.get_or_create(
            user=metadata_user, organization=self.metadata_provider_org
        )
        self.metadata_owner = metadata_owner
        return metadata_owner

    def attach_ref_data_list(
        self,
        legacy_property_name: str,
        target_many_to_many_field: str,
        ref_data_model,
        pref_label_key_name: str = "pref_label",
    ):
        """Method to extract ref-data type lists from dataset_json

        Args:
            legacy_property_name (str): LegacyDataset Class Property method that provides the json field
            target_many_to_many_field (str): ManyToManyField name that will be populated
            ref_data_model (): refdata App Model to use
            pref_label_key_name (str): Some refdata models have different name for pref_label

        Returns:

        """
        obj_list = []
        for obj in getattr(self, legacy_property_name):
            instance, created = ref_data_model.objects.get_or_create(
                url=obj["identifier"],
                defaults={
                    "url": obj["identifier"],
                    "pref_label": obj[pref_label_key_name],
                    "in_scheme": settings.REFERENCE_DATA_SOURCES[target_many_to_many_field].get(
                        "scheme"
                    ),
                },
            )
            obj_list.append(instance)

        # django-simple-history really does not like if trying to access m2m fields from inheritance child-instance.
        # using self.dataset instead of self in order to pass the proper owner of m2m fields to it.
        getattr(self.dataset, target_many_to_many_field).set(obj_list)
        return obj_list

    def attach_spatial(self) -> List[Spatial]:
        if spatial_data := self.legacy_spatial:
            self.dataset.spatial.all().delete()
            obj_list = []
            for location in spatial_data:
                loc_obj = None
                if location.get("identifier"):
                    loc_obj, loc_created = Location.objects.get_or_create(
                        url=location["identifier"],
                        defaults={
                            "in_scheme": location["in_scheme"],
                            "pref_label": location["pref_label"],
                        },
                    )
                spatial = Spatial(
                    reference=loc_obj,
                    dataset=self,
                    geographic_name=location["geographic_name"],
                    full_address=location.get("full_address"),
                )
                if as_wkt := location.get("as_wkt"):
                    if as_wkt != spatial.reference.as_wkt:
                        spatial.custom_wkt = as_wkt
                spatial.save()
                obj_list.append(spatial)
            return obj_list

    def attach_temporal(self):
        records = []
        if temporal := self.legacy_research_dataset.get("temporal"):
            for record in temporal:
                start_date, end_date = self.parse_temporal_timestamps(record)
                instance, created = Temporal.objects.get_or_create(
                    dataset=self,
                    start_date=start_date,
                    end_date=end_date,
                    provenance=None,
                )
                records.append(instance)
        return records

    def attach_other_identifiers(self):
        records = []
        if other_ids := self.legacy_other_identifiers:
            for other_id in other_ids:
                id_type, id_type_created = IdentifierType.objects.get_or_create(
                    in_scheme=other_id["in_scheme"],
                    url=other_id["identifier"],
                    defaults={"pref_label": other_id["pref_label"]},
                )
                instance, created = OtherIdentifier.objects.get_or_create(
                    dataset=self,
                    notation=other_id["notation"],
                    defaults={"identifier_type": id_type},
                )
                records.append(instance)
        self.other_identifiers.set(records)
        return records

    def attach_contract(self) -> Contract:
        if self.legacy_contract:
            contract, created = Contract.objects.get_or_create(
                quota=self.legacy_contract["quota"],
                valid_from=self.legacy_contract["validity"]["start_date"],
                description=self.legacy_contract["description"],
                title={"fi": self.legacy_contract["title"]},
                url=self.legacy_contract["identifier"],
            )
            self.contract = contract
            return contract

    def attach_actor(self, actor_role):
        actors_data = self.legacy_research_dataset[actor_role]

        # In case of publisher, actor is dictionary instead of list
        if isinstance(actors_data, dict):
            actors_data = [actors_data]

        actors = []
        for actor in actors_data:
            dataset_actor = DatasetActor.get_instance_from_v2_dictionary(actor, self, actor_role)
            actors.append(dataset_actor)

        return actors

    def attach_files(self):
        file_objects = []
        if files := self.files_json:
            for f in files:
                file_id = f["identifier"]
                file_checksum = None
                checksum = f.get("checksum", {})

                storage_service = settings.LEGACY_FILE_STORAGE_TO_V3_STORAGE_SERVICE[
                    f["file_storage"]["identifier"]
                ]
                file_storage = get_or_create_file_storage(
                    project_identifier=f["project_identifier"],
                    storage_service=storage_service,
                )

                new_file, created = File.objects.get_or_create(
                    file_storage_identifier=file_id,
                    defaults={
                        "checksum_value": checksum.get("value"),
                        "checksum_algorithm": checksum.get("algorithm"),
                        "checksum_checked": parse_datetime(checksum.get("checked")),
                        "byte_size": f["byte_size"],
                        "file_path": f["file_path"],
                        "date_uploaded": f["date_uploaded"],
                        "file_modified": f["file_modified"],
                        "file_storage_identifier": f["identifier"],
                        "file_storage": file_storage,
                    },
                )
                if file_checksum:
                    new_file.checksum = file_checksum
                file_objects.append(new_file)
        self.files.set(file_objects)
        return file_objects

    def attach_provenance(self):
        """

        Returns: object list

        """
        obj_list = []
        if provenance_data := self.legacy_research_dataset.get("provenance"):
            for data in provenance_data:
                provenance, provenance_created = Provenance.objects.get_or_create(
                    title=data["title"], description=data["description"], dataset=self
                )
                logger.info(f"{provenance=}, created={provenance_created}")
                if spatial_data := data.get("spatial"):
                    if provenance.spatial:
                        provenance.spatial.delete()
                        provenance.spatial = None

                    loc_obj, loc_created = Location.objects.get_or_create(
                        url=spatial_data["place_uri"]["identifier"],
                        defaults={
                            "in_scheme": spatial_data["place_uri"]["in_scheme"],
                            "pref_label": spatial_data["place_uri"]["pref_label"],
                        },
                    )

                    spatial = Spatial(
                        provenance=provenance,
                        full_address=spatial_data.get("full_address"),
                        geographic_name=spatial_data.get("geographic_name"),
                        reference=loc_obj,
                    )
                    if as_wkt := spatial_data.get("as_wkt"):
                        if as_wkt != spatial.reference.as_wkt:
                            spatial.custom_wkt = as_wkt
                    spatial.save()
                    provenance.spatial = spatial
                if temporal_data := data.get("temporal"):
                    start_date, end_date = self.parse_temporal_timestamps(temporal_data)
                    temporal, temporal_created = Temporal.objects.get_or_create(
                        start_date=start_date,
                        end_date=end_date,
                        provenance=provenance,
                        dataset=None,
                    )
                    logger.info(f"{temporal=}, created={temporal_created}")
                if variables := data.get("variable"):
                    for var in variables:
                        (
                            variable,
                            variable_created,
                        ) = ProvenanceVariable.objects.get_or_create(
                            pref_label=var["pref_label"],
                            provenance=provenance,
                            representation=var.get("representation"),
                        )
                if event_outcome_data := data.get("event_outcome"):
                    event_outcome, created = EventOutcome.objects.get_or_create(
                        in_scheme=event_outcome_data["in_scheme"],
                        url=event_outcome_data["identifier"],
                        pref_label=event_outcome_data["pref_label"],
                    )
                    provenance.event_outcome = event_outcome
                if lifecycle_event_data := data.get("lifecycle_event"):
                    lifecycle_event, created = LifecycleEvent.objects.get_or_create(
                        in_scheme=lifecycle_event_data["in_scheme"],
                        url=lifecycle_event_data["identifier"],
                        pref_label=lifecycle_event_data["pref_label"],
                    )
                    provenance.lifecycle_event = lifecycle_event
                associated_with_objs = []
                if was_associated_with := data.get("was_associated_with"):
                    for actor_data in was_associated_with:
                        actor = DatasetActor.get_instance_from_v2_dictionary(
                            actor_data, self, "provenance"
                        )
                        associated_with_objs.append(actor)

                provenance.is_associated_with.set(associated_with_objs)
                if data.get("outcome_description"):
                    provenance.outcome_description = data.get("outcome_description")

                provenance.save()
                obj_list.append(provenance)
        return obj_list

    def attach_projects(self):
        obj_list = []
        if project_data := self.legacy_research_dataset.get("is_output_of"):
            for data in project_data:
                project, created = DatasetProject.objects.get_or_create(
                    name=data["name"],
                    project_identifier=data["identifier"],
                    funder_identifier=data.get("funder_identifier"),
                )
                funder_type, created = FunderType.objects.get_or_create(
                    in_scheme=data["funder_type"]["in_scheme"],
                    url=data["funder_type"]["identifier"],
                    pref_label=data["funder_type"]["pref_label"],
                )
                project.funder_type = funder_type
                funders = []
                participants = []
                for funder in data.get("has_funding_agency", []):
                    org = Organization.get_instance_from_v2_dictionary(funder)
                    funders.append(org)
                for participant in data.get("source_organization", []):
                    org = Organization.get_instance_from_v2_dictionary(participant)
                    participants.append(org)
                project.funding_agency.set(funders)
                project.participating_organization.set(participants)
                project.save()
                obj_list.append(project)
        return obj_list

    def prepare_dataset_for_v3(self) -> PreparedInstances:
        """Define fields and related objects that can be set before save

        Returns:
            PreparedInstances: Created objects

        """
        self.convert_root_level_fields()
        self.convert_research_dataset_fields()

        access_rights = self.attach_access_rights()
        data_catalog = self.attach_data_catalog()
        contract = self.attach_contract()
        metadata_owner = self.attach_metadata_owner()

        access_rights.save()
        data_catalog.save()

        if contract:
            contract.save()

        return PreparedInstances(
            access_rights=access_rights,
            data_catalog=data_catalog,
            contract=contract,
            metadata_owner=metadata_owner,
        )

    def post_process_dataset_for_v3(self) -> PostProcessedInstances:
        """Define fields and related objects that can be set after save

        These are ManyToMany and reverse ForeignKey fields

        Returns:
            PostProcessedInstances: Created objects
        """

        return PostProcessedInstances(
            languages=self.attach_ref_data_list(
                legacy_property_name="legacy_languages",
                target_many_to_many_field="language",
                ref_data_model=Language,
                pref_label_key_name="title",
            ),
            spatial=self.attach_spatial(),
            creators=self.attach_actor("creator"),
            publisher=self.attach_actor("publisher"),
            files=self.attach_files(),
            temporal=self.attach_temporal(),
            other_identifiers=self.attach_other_identifiers(),
            field_of_science=self.attach_ref_data_list(
                legacy_property_name="legacy_field_of_science",
                target_many_to_many_field="field_of_science",
                ref_data_model=FieldOfScience,
            ),
            provenance=self.attach_provenance(),
            projects=self.attach_projects(),
        )

    def check_compatibility(self) -> Dict:
        v3_version = parse_iso_dates_in_nested_dict(self.as_v2_dataset())
        v2_version = parse_iso_dates_in_nested_dict(self.dataset_json)
        diff = DeepDiff(
            v2_version,
            v3_version,
            ignore_order=True,
            exclude_paths=[
                "identifier",
                "id",
                "api_meta",
                "service_modified",
                "service_created",
                "root['data_catalog']['id']",
                "root['research_dataset']['metadata_version_identifier']",
                "root['dataset_version_set']",
                "date_modified",
            ],
            exclude_regex_paths=[
                add_escapes("root['research_dataset']['language'][\\d]['in_scheme']"),
                add_escapes(
                    "root['research_dataset']['access_rights']['license'][\\d]['title']['und']"
                ),
            ],
            truncate_datetime="day",
        )
        logger.info(f"diff={diff.to_json()}")
        json_diff = diff.to_json()
        return json.loads(json_diff)

def add_escapes(val: str):
    val = val.replace("[", "\\[")
    return val.replace("]", "\\]")
