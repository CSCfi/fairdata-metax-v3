import json
import logging
import uuid
from collections import Counter, namedtuple
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from deepdiff import DeepDiff
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import ProgrammingError, models
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.actors.models import Actor, Organization, Person
from apps.common.helpers import datetime_to_date, parse_iso_dates_in_nested_dict
from apps.core.models import FileSet
from apps.files.models import File
from apps.files.serializers.file_serializer import get_or_create_storage
from apps.refdata.models import FunderType, License, Location
from apps.users.models import MetaxUser

from .access_rights import AccessRights
from .catalog_record import (
    Dataset,
    DatasetActor,
    DatasetProject,
    Funder,
    Funding,
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
    ResearchInfra,
    RestrictionGrounds,
    Spatial,
)
from .data_catalog import DataCatalog
from .preservation import Contract
from .provenance import Provenance, ProvenanceVariable

logger = logging.getLogger(__name__)

PreparedInstances = namedtuple(
    "PreparedInstances", ["access_rights", "data_catalog", "contract", "metadata_owner"]
)
PostProcessedInstances = namedtuple(
    "PostProcessedInstances",
    [
        "languages",
        "spatial",
        "creators",
        "file_set",
        "temporal",
        "other_identifiers",
        "field_of_science",
        "infrastructure",
        "provenance",
        "publisher",
        "projects",
    ],
)


class InvalidActorTypeError(Exception):
    def __init__(self, message="Invalid Actor type"):
        super().__init__(message)

        self.message = message


class LegacyDataset(Dataset):
    """Migrated V1 and V2 Datasets

    Stores legacy dataset json fields and derives v3 dataset fields from them using signals.

    Attributes:
        dataset_json (models.JSONField): V1/V2 dataset json from legacy metax dataset API
        contract_json (models.JSONField): Contract json for which the dataset is under
        files_json (models.JSONField): Files attached to the dataset trough dataset/files API in v2
        v2_dataset_compatibility_diff (models.JSONField):
            Difference between v1-v2 and V3 dataset json
    """

    dataset_json = models.JSONField(encoder=DjangoJSONEncoder)
    contract_json = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    files_json = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    v2_dataset_compatibility_diff = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="Difference between v1-v2 and V3 dataset json",
    )
    created_objects = Counter()

    @property
    def is_legacy(self):
        return True

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
        return self.legacy_access_rights.get("license") or []

    @property
    def legacy_data_catalog(self):
        return self.dataset_json["data_catalog"]

    @property
    def legacy_languages(self):
        return self.legacy_research_dataset.get("language")

    @property
    def legacy_field_of_science(self):
        return self.legacy_research_dataset.get("field_of_science") or []

    @property
    def legacy_infrastructure(self):
        return self.legacy_research_dataset.get("infrastructure") or []

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

    def create_snapshot(self, **kwargs):
        """Create snapshot of dataset.

        Due to how simple-history works, LegacyDataset will need to be "cast"
        into a normal Dataset for creating a snapshot or otherwise it will
        raise an error about unknown `dataset_ptr` field.
        """
        self.dataset.create_snapshot(**kwargs)

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
                flatten_obj: Dict
                # Sometimes spatial does not have place_uri top level key
                if obj.get(top_level_key_name):
                    flatten_obj = {**obj[top_level_key_name]}
                else:
                    flatten_obj = {**obj}
                if additional_keys:
                    for key in additional_keys:
                        flatten_obj[key] = obj.get(key)
                obj_list.append(flatten_obj)
            return obj_list

    @classmethod
    def parse_temporal_timestamps(cls, legacy_temporal):
        if start_date := legacy_temporal.get("start_date"):
            if not isinstance(start_date, datetime):
                start_date = parse_datetime(legacy_temporal["start_date"])
            start_date = datetime_to_date(start_date)
        if end_date := legacy_temporal.get("end_date"):
            if not isinstance(end_date, datetime):
                end_date = parse_datetime(legacy_temporal["end_date"])
            end_date = datetime_to_date(end_date)
        return start_date, end_date

    def convert_root_level_fields(self):
        """
        Convert catalog_record top level fields to new Dataset format
        Returns:

        """

        if not self.legacy_identifier:
            raise serializers.ValidationError(
                {"dataset_json__identifier": _("Value is required.")}
            )
        try:
            uuid.UUID(self.legacy_identifier)
        except ValueError:
            raise serializers.ValidationError(
                {"dataset_json__identifier": _("Value is not a valid UUID.")}
            )

        self.cumulation_started = self.dataset_json.get("date_cumulation_started")
        self.cumulation_ended = self.dataset_json.get("date_cumulation_ended")
        self.last_cumulative_addition = self.dataset_json.get("date_last_cumulative_addition")
        self.cumulative_state = self.dataset_json.get("cumulative_state")
        # self.previous = self.dataset_json.get("previous_dataset_version")
        self.created = self.dataset_json.get("date_created")

        if modified := self.legacy_research_dataset.get("modified"):
            self.modified = modified
        elif modified := self.dataset_json.get("date_modified"):
            self.modified = modified
        else:
            self.modified = self.created

        if self.dataset_json.get("deprecated"):
            # Use modification date for deprecation date if not already set
            if not self.deprecated:
                self.deprecated = self.modified
        else:
            self.deprecated = None

        if user_modified := self.dataset_json.get("user_modified"):
            user, created = get_user_model().objects.get_or_create(username=user_modified)
            self.last_modified_by = user
            if created:
                self.created_objects.update(["User"])

        self.preservation_state = self.dataset_json.get("preservation_state")
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
        elif not self.issued:
            self.issued = datetime_to_date(parse_datetime(self.modified))

        if "keyword" in self.legacy_research_dataset:
            self.keyword = self.legacy_research_dataset["keyword"]

    def remove_attached_actors(self):
        attached_actors = DatasetActor.objects.filter(dataset=self)
        attached_user_defined_orgs = Organization.objects.filter(
            actor_organizations__in=attached_actors.values("id"), url__isnull=True
        )
        self.created_objects["DatasetActor"] -= attached_actors.count()
        self.created_objects["Organization"] -= attached_user_defined_orgs.count()
        attached_user_defined_orgs.delete()
        attached_actors.delete()

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
        if at_created:
            self.created_objects.update(["AccessType"])
        if not self.access_rights:
            access_rights = AccessRights(
                access_type=access_type,
                description=description,
            )
            access_rights.save()
            self.created_objects.update(["AccessRights"])
            self.access_rights = access_rights

        # license objects
        licenses_list = self.legacy_license
        license_objects = []
        for lic in licenses_list:
            url = lic.get("identifier")
            if url:
                lic_ref = License.objects.get(url=url)
            else:
                lic_ref = License.objects.get(
                    url="http://uri.suomi.fi/codelist/fairdata/license/code/notspecified"
                )
            custom_url = lic.get("license", None)
            license_instance, created = DatasetLicense.objects.get_or_create(
                access_rights__dataset=self.id,
                reference=lic_ref,
                defaults={
                    "description": lic.get("description"),
                    "custom_url": custom_url,
                },
            )
            if created:
                self.created_objects.update(["DatasetLicense"])
            license_objects.append(license_instance)

        restriction_grounds_objects = []
        for res_grounds in self.legacy_access_rights.get("restriction_grounds", []):
            rg, rg_created = RestrictionGrounds.objects.get_or_create(
                url=res_grounds["identifier"],
                defaults={
                    "pref_label": res_grounds["pref_label"],
                    "in_scheme": res_grounds["in_scheme"],
                },
            )
            if rg_created:
                self.created_objects.update(["RestrictionGrounds"])
            logger.debug(f"restriction_grounds={rg}, created={rg_created}")
            restriction_grounds_objects.append(rg)
        self.access_rights.license.set(license_objects)
        self.access_rights.restriction_grounds.set(restriction_grounds_objects)
        return self.access_rights

    def attach_data_catalog(self) -> DataCatalog:
        if hasattr(self, "data_catalog") and self.data_catalog is not None:
            return self.data_catalog
        catalog_id = self.legacy_data_catalog["identifier"]
        catalog, created = DataCatalog.objects.get_or_create(
            id=catalog_id, defaults={"id": catalog_id, "title": {"und": catalog_id}}
        )
        if created:
            self.created_objects.update(["DataCatalog"])
        self.data_catalog = catalog
        return catalog

    def attach_metadata_owner(self) -> Actor:
        """Creates new Actor-object from metadata-owner field, that is usually CSC-username"""
        metadata_user, user_created = MetaxUser.objects.get_or_create(
            username=self.metadata_provider_user
        )
        owner_created = False
        metadata_owner = MetadataProvider.objects.filter(
            user=metadata_user, organization=self.metadata_provider_org
        ).first()
        if not metadata_owner:
            metadata_owner = MetadataProvider.objects.create(
                user=metadata_user, organization=self.metadata_provider_org
            )
            owner_created = True
        if owner_created:
            self.created_objects.update(["MetadataProvider"])
        if user_created:
            self.created_objects.update(["User"])
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
        if not getattr(self, legacy_property_name):
            return obj_list
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
            if created:
                self.created_objects.update([target_many_to_many_field])
            obj_list.append(instance)

        # django-simple-history really does not like if trying to access m2m fields from inheritance child-instance.
        # using self.dataset instead of self in order to pass the proper owner of m2m fields to it.
        getattr(self.dataset, target_many_to_many_field).set(obj_list)
        return obj_list

    def attach_spatial(self) -> List[Spatial]:
        if spatial_data := self.legacy_spatial:
            self.created_objects["Spatial"] -= self.dataset.spatial.all().count()
            self.dataset.spatial.all().delete()
            obj_list = []
            for data in spatial_data:
                loc_obj = None
                if data.get("identifier"):
                    loc_obj, loc_created = Location.objects.get_or_create(
                        url=data["identifier"],
                        defaults={
                            "in_scheme": data["in_scheme"],
                            "pref_label": data["pref_label"],
                        },
                    )
                    if loc_created:
                        self.created_objects.update(["Location"])
                spatial = Spatial(
                    reference=loc_obj,
                    dataset=self,
                    geographic_name=data["geographic_name"],
                    full_address=data.get("full_address"),
                )
                self.created_objects.update(["Spatial"])
                if data.get("as_wkt") and spatial.reference:
                    as_wkt = data.get("as_wkt")
                    if as_wkt != spatial.reference.as_wkt:
                        spatial.custom_wkt = as_wkt
                try:
                    spatial.save()
                except ProgrammingError as e:
                    logger.error(
                        f"Failed to save {spatial=}, with {data=}, and reference {loc_obj}"
                    )
                    raise e
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
                if created:
                    self.created_objects.update(["Temporal"])
                records.append(instance)
        return records

    def attach_other_identifiers(self):
        records = []
        if other_ids := self.legacy_other_identifiers:
            for other_id in other_ids:
                id_type = None
                if other_id.get("identifier"):
                    id_type, id_type_created = IdentifierType.objects.get_or_create(
                        url=other_id["identifier"],
                        defaults={
                            "pref_label": other_id["pref_label"],
                            "in_scheme": other_id["in_scheme"],
                        },
                    )
                    if id_type_created:
                        self.created_objects.update(["IdentifierType"])
                instance, created = OtherIdentifier.objects.get_or_create(
                    dataset=self,
                    notation=other_id["notation"],
                    defaults={"identifier_type": id_type},
                )
                if created:
                    self.created_objects.update(["OtherIdentifier"])
                records.append(instance)

        self.dataset.other_identifiers.set(records)
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
            if created:
                self.created_objects.update(["Contract"])
            self.contract = contract
            return contract

    def attach_actor(self, actor_role):
        if actors_data := self.legacy_research_dataset.get(actor_role):
            # In case of publisher, actor is dictionary instead of list
            if isinstance(actors_data, dict):
                actors_data = [actors_data]

            actors = []
            for actor in actors_data:
                dataset_actor, created = self.get_or_create_v3_actor_from_v2_actor(
                    actor, actor_role
                )
                if created:
                    self.created_objects.update(["DatasetActor"])
                actors.append(dataset_actor)

            return actors
        return []

    def convert_checksum_v2_to_v3(self, checksum: dict) -> str:
        algorithm = checksum.get("algorithm", "").lower().replace("-", "")
        value = checksum.get("value", "").lower()
        return f"{algorithm}:{value}"

    def attach_files(self):
        storage_file_objects = {}
        if files := self.files_json:
            for f in files:
                file_id = f["identifier"]
                file_checksum = None
                checksum = f.get("checksum", {})

                storage_service = settings.LEGACY_FILE_STORAGE_TO_V3_STORAGE_SERVICE[
                    f["file_storage"]["identifier"]
                ]
                storage = get_or_create_storage(
                    csc_project=f["project_identifier"],
                    storage_service=storage_service,
                )
                new_file, created = File.objects.get_or_create(
                    storage_identifier=file_id,
                    defaults={
                        "checksum": self.convert_checksum_v2_to_v3(checksum),
                        "size": f["byte_size"],
                        "pathname": f["file_path"],
                        "modified": f["file_modified"],
                        "storage_identifier": f["identifier"],
                        "storage": storage,
                    },
                )
                if created:
                    self.created_objects.update(["File"])
                if file_checksum:
                    new_file.checksum = file_checksum

                storage_file_objects.setdefault(storage.id, []).append(new_file)

        file_set = None
        for storage_id, file_objects in storage_file_objects.items():
            file_set, created = FileSet.objects.get_or_create(dataset=self, storage_id=storage_id)
            if created:
                self.created_objects.update(["FileSet"])
            file_set.files.set(file_objects)
        return file_set

    def attach_provenance(self):
        """

        Returns: object list

        """
        obj_list = []
        if provenance_data := self.legacy_research_dataset.get("provenance"):
            for data in provenance_data:
                provenance: Provenance
                provenance_created: bool
                provenance, provenance_created = Provenance.objects.get_or_create(
                    title=data.get("title"), description=data["description"], dataset=self
                )
                if provenance_created:
                    self.created_objects.update(["Provenance"])
                logger.debug(f"{provenance=}, created={provenance_created}")
                if spatial_data := data.get("spatial"):
                    if provenance.spatial:
                        provenance.spatial.delete()
                        self.created_objects["Spatial"] -= 1
                        provenance.spatial = None

                    loc_obj, loc_created = Location.objects.get_or_create(
                        url=spatial_data["place_uri"]["identifier"],
                        defaults={
                            "in_scheme": spatial_data["place_uri"]["in_scheme"],
                            "pref_label": spatial_data["place_uri"]["pref_label"],
                        },
                    )
                    if loc_created:
                        self.created_objects.update(["Location"])

                    spatial = Spatial(
                        provenance=provenance,
                        full_address=spatial_data.get("full_address"),
                        geographic_name=spatial_data.get("geographic_name"),
                        reference=loc_obj,
                    )
                    self.created_objects.update(["Spatial"])
                    if as_wkt := spatial_data.get("as_wkt"):
                        if as_wkt != spatial.reference.as_wkt:
                            spatial.custom_wkt = as_wkt
                    spatial.save()
                    provenance.spatial = spatial
                if temporal_data := data.get("temporal"):
                    start_date, end_date = self.parse_temporal_timestamps(temporal_data)
                    temporal, temporal_created = Temporal.objects.get_or_create(
                        provenance=provenance,
                        dataset=None,
                        defaults={"start_date": start_date, "end_date": end_date},
                    )
                    if temporal_created:
                        self.created_objects.update(["Temporal"])
                    logger.debug(f"{temporal=}, created={temporal_created}")
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
                        if variable_created:
                            self.created_objects.update(["Variable"])
                if event_outcome_data := data.get("event_outcome"):
                    event_outcome, created = EventOutcome.objects.get_or_create(
                        url=event_outcome_data["identifier"],
                        defaults={
                            "pref_label": event_outcome_data["pref_label"],
                            "in_scheme": event_outcome_data["in_scheme"],
                        },
                    )
                    if created:
                        self.created_objects.update(["EventOutcome"])
                    provenance.event_outcome = event_outcome
                if lifecycle_event_data := data.get("lifecycle_event"):
                    lifecycle_event, created = LifecycleEvent.objects.get_or_create(
                        url=lifecycle_event_data["identifier"],
                        defaults={
                            "pref_label": lifecycle_event_data["pref_label"],
                            "in_scheme": lifecycle_event_data["in_scheme"],
                        },
                    )
                    if created:
                        self.created_objects.update(["LifecycleEvent"])
                    provenance.lifecycle_event = lifecycle_event
                associated_with_objs: List[DatasetActor] = []
                if was_associated_with := data.get("was_associated_with"):
                    for actor_data in was_associated_with:
                        actor, created = self.get_or_create_v3_actor_from_v2_actor(
                            actor_data, "provenance"
                        )
                        associated_with_objs.append(actor)

                provenance.is_associated_with.set(associated_with_objs)
                if data.get("outcome_description"):
                    provenance.outcome_description = data.get("outcome_description")

                provenance.save()
                obj_list.append(provenance)
        return obj_list

    @classmethod
    def choose_between_orgs(cls, a, b) -> "Organization":
        """Choose the best option between the orgs when migrating v2 org to v3."""
        if isinstance(a, b.__class__):
            if a.parent is None and b.parent is not None:
                return a
            elif a.in_scheme and not b.in_scheme:
                return a
            elif a.code and not b.code:
                return a
            elif a.url and not b.url:
                return a
            elif len(list(a.pref_label.keys())) > len(list(b.pref_label.keys())):
                return a
            else:
                return b

    @classmethod
    def get_or_create_v3_org_from_v2_org(cls, v2_org) -> "Organization":
        """Get or create organization from v2 organization object.

        Args:
            v2_org (): dictionary with organization name in one or many languages.
                Example dictionary could be {"fi":"csc": "en":"csc"}

        Returns:
            Organization: Organization object corresponding to given name dictionary.

        """
        # https://docs.djangoproject.com/en/4.1/ref/contrib/postgres/fields/#values
        # pref_label is HStoreField that serializes into dictionary object.
        # pref_label__values works as normal python dictionary.values()
        # pref_label__values__contains compares if any given value in a list
        #       is contained in the pref_label values.
        if v2_org["@type"] == "Person":
            raise InvalidActorTypeError()

        parent = None
        if is_part_of := v2_org.get("is_part_of"):
            parent = cls.get_or_create_v3_org_from_v2_org(is_part_of)
        try:
            org, created = Organization.objects.get_or_create(
                pref_label__values__contains=list(v2_org["name"].values()),
                url=v2_org.get("identifier"),
                defaults={
                    "pref_label": v2_org["name"],
                    "homepage": v2_org.get("homepage"),
                    "url": v2_org.get("identifier"),
                    "in_scheme": settings.ORGANIZATION_SCHEME,
                    "parent": parent,
                },
            )
            if created:
                cls.created_objects.update(["Organization"])

            return org
        except MultipleObjectsReturned as e:
            orgs = Organization.objects.filter(
                pref_label__values__contains=list(v2_org["name"].values()),
                url=v2_org.get("identifier"),
            )
            best_org = orgs[0]
            for org in orgs:
                best_org = cls.choose_between_orgs(best_org, org)
            logger.error(
                f"{e}, chose: {best_org.pref_label} from: {[org.pref_label for org in orgs]}"
            )
            return best_org

    def get_or_create_organizations_from_list(self, orgs):
        return [self.get_or_create_v3_org_from_v2_org(org_v2) for org_v2 in orgs]

    def get_or_create_v3_actor_from_v2_actor(
        cls, obj: Dict, role: str
    ) -> Tuple[DatasetActor, bool]:
        """

        Args:
            obj (Dict): v2 actor dictionary
            dataset (Dataset): Dataset where the actor will be present
            role (str): Role of the actor in the dataset

        Returns:
            DatasetActor: get or created DatasetActor instance

        """
        organization: Optional[Organization] = None
        person: Optional[Person] = None

        try:
            organization = cls.get_or_create_v3_org_from_v2_org(obj)
            actor, created = DatasetActor.objects.get_or_create(
                organization=organization, person__isnull=True, dataset=cls
            )
        except InvalidActorTypeError:
            name = obj.get("name")
            person = Person(name=name)
            person.save()
            cls.created_objects.update(["Person"])

            if member_of := obj.get("member_of"):
                organization = cls.get_or_create_v3_org_from_v2_org(member_of)
            actor, created = DatasetActor.objects.get_or_create(
                organization=organization, dataset=cls, person=person
            )

        except Exception as e:
            logger.error(f"{e}\nin dataset: {cls.id}\nattaching actor: {obj}")
            raise e

        if not actor.roles:
            actor.roles = [role]
        elif role not in actor.roles:
            actor.roles.append(role)

        actor.save()

        if created:
            cls.created_objects.update(["DatasetActor"])

        return actor, created

    def create_funding(self, data, funder_org):
        funder_type = None

        if funder_type_id := data.get("funder_type", {}).get("identifier"):
            try:
                funder_type = FunderType.objects.get(url=funder_type_id)
            except ObjectDoesNotExist as e:
                logger.warn(f"{e}: {funder_type_id=}")

        funder = Funder.objects.create(organization=funder_org, funder_type=funder_type)
        funder.save()
        self.created_objects.update(["Funder"])
        fund = Funding.objects.create(
            funder=funder, funding_identifier=data.get("has_funder_identifier", None)
        )
        fund.save()
        self.created_objects.update(["Funding"])
        return fund

    def attach_projects(self):
        obj_list = []

        if project_data := self.legacy_research_dataset.get("is_output_of"):
            for data in project_data:
                funding = []
                source_organizations = self.get_or_create_organizations_from_list(
                    data.get("source_organization", [])
                )
                funder_organizations = self.get_or_create_organizations_from_list(
                    data.get("has_funding_agency", [])
                )

                for funder_org in funder_organizations:
                    fund = self.create_funding(data, funder_org)
                    funding.append(fund)

                project, created = DatasetProject.objects.get_or_create(
                    dataset=self,
                    title=data["name"],
                    defaults={
                        "project_identifier": data.get("identifier"),
                    },
                )

                project.participating_organizations.set(source_organizations)
                project.funding.set(funding)

                if created:
                    self.created_objects.update(["DatasetProject"])
                    project.dataset = self

                obj_list.append(project)
        return obj_list

    def prepare_dataset_for_v3(self) -> PreparedInstances:
        """Define fields and related objects that can be set before save

        Returns:
            PreparedInstances: Created objects

        """
        self.convert_root_level_fields()
        self.convert_research_dataset_fields()
        self.remove_attached_actors()

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
            file_set=self.attach_files(),
            temporal=self.attach_temporal(),
            other_identifiers=self.attach_other_identifiers(),
            field_of_science=self.attach_ref_data_list(
                legacy_property_name="legacy_field_of_science",
                target_many_to_many_field="field_of_science",
                ref_data_model=FieldOfScience,
            ),
            infrastructure=self.attach_ref_data_list(
                legacy_property_name="legacy_infrastructure",
                target_many_to_many_field="infrastructure",
                ref_data_model=ResearchInfra,
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
            cutoff_intersection_for_pairs=0.9,
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
                add_escapes("root['research_dataset']['language'][\\d]['pref_label']"),
                add_escapes(
                    "root['research_dataset']['access_rights']['license'][\\d]['title']['und']"
                ),
            ],
            truncate_datetime="day",
        )
        # logger.info(f"diff={diff.to_json()}")
        json_diff = diff.to_json()
        return json.loads(json_diff)

    def save(self, *args, **kwargs):
        attached_instances = self.prepare_dataset_for_v3()
        logger.debug(f"prepared {attached_instances=}")

        if str(self.id) != str(self.legacy_identifier):
            raise serializers.ValidationError({"id": _("Value does not match V2 identifier.")})

        if Dataset.objects.filter(id=self.id, legacydataset__isnull=True).exists():
            raise serializers.ValidationError(
                {"id": _("A non-legacy dataset already exists with the same identifier.")}
            )

        return super().save(*args, **kwargs)


def add_escapes(val: str):
    val = val.replace("[", "\\[")
    return val.replace("]", "\\]")
