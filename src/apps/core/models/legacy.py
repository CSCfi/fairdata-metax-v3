import json
import logging
import uuid
from collections import Counter, namedtuple
from datetime import datetime
from typing import Dict, List, Optional

from dateutil.parser import parse
from deepdiff import DeepDiff
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.actors.models import Actor
from apps.common.helpers import datetime_to_date, parse_iso_dates_in_nested_dict
from apps.core.models import FileSet
from apps.files.models import File
from apps.files.serializers.file_serializer import get_or_create_storage
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
)
from .concepts import (
    AccessType,
    DatasetLicense,
    EventOutcome,
    FieldOfScience,
    FileType,
    FunderType,
    IdentifierType,
    Language,
    License,
    LifecycleEvent,
    Location,
    RelationType,
    ResearchInfra,
    ResourceType,
    RestrictionGrounds,
    Spatial,
    Theme,
    UseCategory,
)
from .data_catalog import DataCatalog
from .preservation import Contract
from .provenance import Provenance

logger = logging.getLogger(__name__)

PreparedInstances = namedtuple(
    "PreparedInstances", ["access_rights", "data_catalog", "contract", "metadata_owner"]
)
PostProcessedInstances = namedtuple(
    "PostProcessedInstances",
    [
        "languages",
        "spatial",
        "actors",
        "file_set",
        "temporal",
        "other_identifiers",
        "field_of_science",
        "infrastructure",
        "provenance",
        "projects",
        "relations",
        "theme",
        "remote_resources",
    ],
)


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
        if "license" in self.legacy_access_rights:
            return self.legacy_access_rights["license"]
        else:
            return []

    @property
    def legacy_data_catalog(self):
        return self.dataset_json["data_catalog"]

    @property
    def legacy_languages(self):
        if "language" in self.legacy_research_dataset:
            return self.legacy_research_dataset["language"]
        else:
            return []

    @property
    def legacy_field_of_science(self):
        if "field_of_science" in self.legacy_research_dataset:
            return self.legacy_research_dataset["field_of_science"]
        else:
            return []

    @property
    def legacy_infrastructure(self):
        return self.legacy_research_dataset.get("infrastructure") or []

    @property
    def legacy_theme(self):
        return self.legacy_research_dataset.get("theme") or []

    @property
    def legacy_spatial(self):
        return self.legacy_research_dataset.get("spatial") or []

    @property
    def legacy_other_identifiers(self):
        return self.legacy_research_dataset.get("other_identifier") or []

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

    def attach_access_rights(self) -> AccessRights:
        description = self.legacy_access_rights.get("description", None)
        available = self.legacy_access_rights.get("available", None)

        if available:
            available = parse(available)
        # access-type object
        access_type, at_created = self.get_or_create_reference_data(
            AccessType,
            url=self.legacy_access_type["identifier"],
            defaults={
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
                available=available,
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
                custom_url=custom_url,
                defaults={
                    "description": lic.get("description"),
                },
            )
            if created:
                self.created_objects.update(["DatasetLicense"])
            license_objects.append(license_instance)

        restriction_grounds_objects = []
        for res_grounds in self.legacy_access_rights.get("restriction_grounds", []):
            rg, rg_created = self.get_or_create_reference_data(
                RestrictionGrounds,
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
            id=catalog_id, defaults={"title": {"und": catalog_id}}
        )
        if created:
            self.created_objects.update(["DataCatalog"])
        self.data_catalog = catalog
        return catalog

    def attach_metadata_owner(self) -> Actor:
        """Creates new MetadataProvider object from metadata-owner field, that is usually CSC-username"""
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

    def get_or_create_reference_data(self, ref_data_model, url: str, defaults: dict) -> tuple:
        instance, created = ref_data_model.objects.get_or_create(
            url=url, defaults={**defaults, "deprecated": timezone.now()}
        )
        if created:
            logger.info(
                f"Created reference data for {ref_data_model.__name__}: {dict(url=url, **defaults)}"
            )
        return instance, created

    def convert_reference_data(self, ref_data_model, concept: dict, overrides = {}) -> Optional[dict]:
        if not concept:
            return None
        instance, created = self.get_or_create_reference_data(
            ref_data_model=ref_data_model,
            url=concept["identifier"],
            defaults={
                "pref_label": concept.get("pref_label"),
                "in_scheme": concept.get("in_scheme"),
                **overrides,
            },
        )
        return {"url": instance.url}

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
            instance, created = self.get_or_create_reference_data(
                ref_data_model,
                url=obj["identifier"],
                defaults={
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

    def convert_spatial(self, spatial: dict) -> Optional[dict]:
        if not spatial:
            return None
        location = None
        if location_data := spatial.get("place_uri"):
            location = self.convert_reference_data(
                Location,
                {
                    "identifier": location_data["identifier"],
                    "in_scheme": location_data["in_scheme"],
                    "pref_label": location_data["pref_label"],
                },
            )

        obj = {
            "reference": location,
            "geographic_name": spatial.get("geographic_name"),
            "full_address": spatial.get("full_address"),
        }
        if spatial.get("as_wkt"):
            location_wkt = None
            if location:
                location_wkt = (
                    Location.objects.filter(url=location.get("url"))
                    .values_list("as_wkt", flat=True)
                    .first()
                )

            as_wkt = spatial.get("as_wkt")
            if as_wkt != [location_wkt]:
                obj["custom_wkt"] = as_wkt
        return obj

    def attach_spatial(self) -> List[Spatial]:
        spatial_data = [
            self.convert_spatial(spatial)
            for spatial in self.legacy_research_dataset.get("spatial", [])
        ]
        from apps.core.serializers import SpatialModelSerializer

        serializer = SpatialModelSerializer(
            instance=self.spatial.all(), data=spatial_data, many=True
        )
        serializer.is_valid(raise_exception=True)
        spatials = serializer.save()
        self.spatial.set(spatials)
        return spatials

    def convert_temporal(self, temporal: dict) -> Optional[dict]:
        if not temporal:
            return None
        start_date, end_date = self.parse_temporal_timestamps(temporal)
        return {
            "start_date": start_date,
            "end_date": end_date,
        }

    def attach_temporal(self):
        temporal_data = [
            self.convert_temporal(temporal)
            for temporal in self.legacy_research_dataset.get("temporal", [])
        ]
        from apps.core.serializers import TemporalModelSerializer

        serializer = TemporalModelSerializer(
            instance=self.temporal.all(), data=temporal_data, many=True
        )
        serializer.is_valid(raise_exception=True)
        temporals = serializer.save()
        self.temporal.set(temporals)
        return temporals

    def convert_other_identifier(self, other_identifier: dict) -> dict:
        return {
            "notation": other_identifier.get("notation"),
            "identifier_type": self.convert_reference_data(
                IdentifierType, other_identifier.get("type")
            ),
        }

    def attach_other_identifiers(self) -> List[OtherIdentifier]:
        identifier_data = [
            self.convert_other_identifier(obj) for obj in self.legacy_other_identifiers
        ]
        from apps.core.serializers import OtherIdentifierModelSerializer

        serializer = OtherIdentifierModelSerializer(
            instance=self.other_identifiers.all(), data=identifier_data, many=True
        )
        serializer.is_valid(raise_exception=True)
        other_identifiers = serializer.save()
        self.other_identifiers.set(other_identifiers)
        return other_identifiers

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

    def convert_homepage(self, homepage):
        if not homepage:
            return homepage
        return {"title": homepage.get("title"), "url": homepage.get("identifier")}

    def convert_organization(self, organization: dict) -> dict:
        """Convert organization from V2 dict to V3 dict."""
        val = {
            "pref_label": organization.get("name"),
            "email": organization.get("email"),
            "homepage": self.convert_homepage(organization.get("homepage")),
        }
        if identifier := organization.get("identifier"):
            if identifier.startswith(settings.ORGANIZATION_BASE_URI):
                val["url"] = identifier  # reference data
            else:
                val["external_identifier"] = identifier

        if parent := organization.get("is_part_of"):
            val["parent"] = self.convert_organization(parent)
        return val

    def convert_actor(self, actor: dict) -> dict:
        """Convert actor from V2 dict (optionally with roles) to V3 dict."""
        val = {}
        if actor["@type"] == "Person":
            val["person"] = {
                "name": actor.get("name"),
                "external_identifier": actor.get("identifier"),
                "email": actor.get("email"),
            }
            if parent := actor.get("member_of"):
                val["organization"] = self.convert_organization(parent)
        elif actor["@type"] == "Organization":
            val["organization"] = self.convert_organization(actor)
        else:
            # Agent (which should be unused) is not supported
            logger.warn(f"Unknown actor type: {actor['@type']}")

        if roles := actor.get("roles"):
            # The actor serializer combines actors that have multiple roles
            # so it's ok to output multiple copies of same actor here
            val["roles"] = roles

        return val

    def attach_actors(self) -> List[DatasetActor]:
        actors_data = []
        roles = ["creator", "publisher", "curator", "contributor", "rights_holder"]
        for role in roles:
            # Flatten actors list and add role data
            role_actors = self.legacy_research_dataset.get(role) or []
            if isinstance(role_actors, dict):
                role_actors = [role_actors]  # Publisher is dictionary instead of list
            actors_data.extend([{**actor, "roles": [role]} for actor in role_actors])

        adapted = [self.convert_actor(actor) for actor in actors_data]

        from apps.core.serializers.dataset_actor_serializers.legacy_serializers import (
            LegacyDatasetActorSerializer,
        )

        serializer = LegacyDatasetActorSerializer(
            instance=self.actors.all(), data=adapted, context={"dataset": self}, many=True
        )
        serializer.is_valid(raise_exception=True)
        actors = serializer.save()
        self.actors.set(actors)
        return actors

    def convert_checksum_v2_to_v3(self, checksum: dict) -> Optional[str]:
        if not checksum:
            return None
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

    def convert_concept(self, variable: dict) -> Optional[dict]:
        if not variable:
            return None
        return {
            "pref_label": variable.get("pref_label"),
            "definition": variable.get("definition"),
            "concept_identifier": variable.get("identifier"),
            "in_scheme": variable.get("in_scheme"),
        }

    def convert_variable(self, variable: dict) -> dict:
        return {
            "pref_label": variable.get("pref_label"),
            "description": variable.get("description"),
            "concept": self.convert_concept(variable.get("concept")),
            "universe": self.convert_concept(variable.get("universe")),
            "representation": variable.get("representation"),
        }

    def convert_provenance(self, provenance: dict) -> dict:
        return {
            "title": provenance.get("title"),
            "description": provenance.get("description"),
            "outcome_description": provenance.get("outcome_description"),
            "spatial": self.convert_spatial(provenance.get("spatial")),  # maybe None
            "temporal": self.convert_temporal(provenance.get("temporal")),  # maybe None
            "event_outcome": self.convert_reference_data(
                EventOutcome, provenance.get("event_outcome")
            ),
            "lifecycle_event": self.convert_reference_data(
                LifecycleEvent, provenance.get("lifecycle_event")
            ),
            "variables": [self.convert_variable(var) for var in provenance.get("variable", [])],
            "is_associated_with": [
                self.convert_actor(actor) for actor in provenance.get("was_associated_with", [])
            ],
        }

    def attach_provenance(self) -> List[Provenance]:
        provenance_data = [
            self.convert_provenance(prov)
            for prov in self.legacy_research_dataset.get("provenance", [])
        ]
        from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

        serializer = ProvenanceModelSerializer(
            instance=self.provenance.all(),
            data=provenance_data,
            many=True,
            context={"dataset": self},
        )
        serializer.is_valid(raise_exception=True)
        provenances = serializer.save()
        self.provenance.set(provenances)
        return provenances

    def convert_entity(self, entity: dict) -> dict:
        entity_type = None
        if entity_type_data := entity.get("type"):
            entity_type = self.convert_reference_data(ResourceType, entity_type_data)

        return {
            "title": entity.get("title"),
            "description": entity.get("description"),
            "entity_identifier": entity.get("identifier"),
            "type": entity_type,
        }

    def convert_relation(self, relation: dict) -> dict:
        relation_type_scheme = settings.LOCAL_REFERENCE_DATA_SOURCES["relation_type"]["scheme"]
        relation_type, created = self.get_or_create_reference_data(
            RelationType,
            url=relation["relation_type"]["identifier"],
            defaults={
                "pref_label": relation["relation_type"]["pref_label"],
                "in_scheme": relation_type_scheme,
                # TODO: Create deprecated object if not found
            },
        )

        return {
            "entity": self.convert_entity(relation.get("entity")),
            "relation_type": {"url": relation_type.url},
        }

    def attach_relations(self):
        relation_data = [
            self.convert_relation(relation)
            for relation in self.legacy_research_dataset.get("relation", [])
        ]

        from apps.core.serializers.common_serializers import EntityRelationSerializer

        serializer = EntityRelationSerializer(
            instance=self.relation.all(),
            data=relation_data,
            many=True,
        )
        serializer.is_valid(raise_exception=True)
        relations = serializer.save()
        self.relation.set(relations)
        return relations

    def convert_remote_resource(self, resource: dict) -> dict:
        title = None
        if v2_title := resource.get("title"):
            title = {"en": v2_title}

        description = None
        if v2_description := resource.get("description"):
            description = {"en": v2_description}

        use_category = None
        if v2_use_category := resource.get("use_category"):
            ref, created = self.get_or_create_reference_data(
                UseCategory,
                url=v2_use_category["identifier"],
                defaults={
                    "in_scheme": v2_use_category["in_scheme"],
                    "pref_label": v2_use_category["pref_label"],
                },
            )
            use_category = {"url": ref.url}

        file_type = None
        if v2_file_type := resource.get("file_type"):
            ref, created = self.get_or_create_reference_data(
                FileType,
                url=v2_file_type["identifier"],
                defaults={
                    "in_scheme": v2_file_type["in_scheme"],
                    "pref_label": v2_file_type["pref_label"],
                },
            )
            file_type = {"url": ref.url}

        access_url = (resource.get("access_url") or {}).get("identifier")
        download_url = (resource.get("download_url") or {}).get("identifier")

        return {
            "title": title,
            "description": description,
            "checksum": self.convert_checksum_v2_to_v3(resource.get("checksum")),
            "mediatype": resource.get("mediatype"),
            "use_category": use_category,
            "file_type": file_type,
            "access_url": access_url,
            "download_url": download_url,
        }

    def attach_remote_resources(self):
        resource_data = [
            self.convert_remote_resource(resource)
            for resource in self.legacy_research_dataset.get("remote_resources", [])
        ]

        from apps.core.serializers.common_serializers import RemoteResourceSerializer

        serializer = RemoteResourceSerializer(
            instance=self.remote_resources.all(),
            data=resource_data,
            many=True,
            context={"dataset": self},
        )
        serializer.is_valid(raise_exception=True)
        resources = serializer.save()
        self.remote_resources.set(resources)
        return resources

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
        from apps.core.serializers.dataset_actor_serializers.legacy_serializers import (
            LegacyDatasetOrganizationSerializer,
        )

        obj_list = []
        serializer_context = {"dataset": self}

        if project_data := self.legacy_research_dataset.get("is_output_of"):
            for data in project_data:
                project, created = DatasetProject.objects.get_or_create(
                    dataset=self,
                    title=data["name"],
                    defaults={
                        "project_identifier": data.get("identifier"),
                    },
                )

                # Source organizations
                source_data = [
                    self.convert_organization(org) for org in data.get("source_organization", [])
                ]
                source_serializer = LegacyDatasetOrganizationSerializer(
                    instance=project.participating_organizations.all(),
                    data=source_data,
                    context=serializer_context,
                    many=True,
                )
                source_serializer.is_valid(raise_exception=True)
                source_organizations = source_serializer.save()
                project.participating_organizations.set(source_organizations)

                # Funder organizations
                funder_data = [
                    self.convert_organization(org) for org in data.get("has_funding_agency", [])
                ]
                funder_serializer = LegacyDatasetOrganizationSerializer(
                    data=funder_data, context=serializer_context, many=True
                )
                funder_serializer.is_valid(raise_exception=True)
                funder_organizations = funder_serializer.save()

                funding = []
                for funder_org in funder_organizations:
                    fund = self.create_funding(data, funder_org)
                    funding.append(fund)
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
            actors=self.attach_actors(),
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
            theme=self.attach_ref_data_list(
                legacy_property_name="legacy_theme",
                target_many_to_many_field="theme",
                ref_data_model=Theme,
            ),
            provenance=self.attach_provenance(),
            projects=self.attach_projects(),
            relations=self.attach_relations(),
            remote_resources=self.attach_remote_resources(),
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
