import copy
import json
import logging
import uuid
from collections import Counter
from typing import Dict, Optional

from deepdiff import DeepDiff
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.actors.models import Actor, Organization
from apps.common.helpers import (
    datetime_to_date,
    ensure_dict,
    ensure_list,
    omit_none,
    parse_iso_dates_in_nested_dict,
)
from apps.core.models import FileSet
from apps.files.models import File
from apps.files.serializers.file_serializer import get_or_create_storage
from apps.users.models import MetaxUser

from .catalog_record import Dataset, MetadataProvider
from .concepts import (
    AccessType,
    EventOutcome,
    FieldOfScience,
    FileType,
    FunderType,
    IdentifierType,
    Language,
    LifecycleEvent,
    Location,
    RelationType,
    ResearchInfra,
    ResourceType,
    RestrictionGrounds,
    Theme,
    UseCategory,
)
from .data_catalog import DataCatalog
from .preservation import Contract

logger = logging.getLogger(__name__)


class LegacyDataset(Dataset):
    """Migrated V1 and V2 Datasets

    Stores legacy dataset json fields and derives v3 dataset
    fields from them when update_from_legacy is called.

    Attributes:
        dataset_json (models.JSONField): V1/V2 dataset json from legacy metax dataset API
        contract_json (models.JSONField): Contract json for which the dataset is under
        files_json (models.JSONField): Files attached to the dataset trough dataset/files API in v2
        v2_dataset_compatibility_diff (models.JSONField):
            Difference between v1-v2 and V3 dataset json
    """

    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )
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

    def __init__(self, *args, convert_only=False, **kwargs):
        super().__init__(*args, **kwargs)

        # When convert_only is enabled, dataset is not saved
        # and no reference data is created during V2->V3 conversion.
        self.convert_only = convert_only
        if not convert_only and self._state.adding:
            # Get minimal dataset fields from legacy json
            if not self.metadata_owner_id:
                self.attach_metadata_owner()
            if not self.title:
                self.title = self.legacy_research_dataset["title"]

    @property
    def is_legacy(self):
        return True

    @property
    def legacy_identifier(self):
        """Legacy database primary key"""
        return self.dataset_json.get("identifier")

    @property
    def legacy_persistent_identifier(self):
        """Resolvable persistent identifier like DOI or URN"""
        return self.legacy_research_dataset.get("preferred_identifier")

    @property
    def metadata_provider_user(self):
        return self.dataset_json.get("metadata_provider_user")

    @property
    def metadata_provider_org(self):
        if org := self.dataset_json.get("metadata_provider_org"):
            return org
        else:
            return self.dataset_json.get("metadata_owner_org")

    @property
    def legacy_research_dataset(self):
        return ensure_dict(self.dataset_json.get("research_dataset") or {})

    @property
    def legacy_access_rights(self):
        return ensure_dict(self.legacy_research_dataset.get("access_rights") or {})

    @property
    def legacy_access_type(self):
        return self.legacy_access_rights.get("access_type")

    @property
    def legacy_license(self):
        return ensure_list(self.legacy_access_rights.get("license"))

    @property
    def legacy_data_catalog(self):
        return self.dataset_json.get("data_catalog")

    @property
    def legacy_languages(self):
        return ensure_list(self.legacy_research_dataset.get("language"))

    @property
    def legacy_field_of_science(self):
        return ensure_list(self.legacy_research_dataset.get("field_of_science"))

    @property
    def legacy_infrastructure(self):
        return ensure_list(self.legacy_research_dataset.get("infrastructure"))

    @property
    def legacy_theme(self):
        return ensure_list(self.legacy_research_dataset.get("theme"))

    @property
    def legacy_spatial(self):
        return ensure_list(self.legacy_research_dataset.get("spatial"))

    @property
    def legacy_other_identifiers(self):
        return ensure_list(self.legacy_research_dataset.get("other_identifier"))

    @property
    def legacy_contract(self):
        if self.contract_json:
            return self.contract_json["contract_json"]

    def create_snapshot(self, **kwargs):
        """Create snapshot of dataset.

        Due to how simple-history works, LegacyDataset will need to be "cast"
        into a normal Dataset for creating a snapshot.
        """
        self.dataset.create_snapshot(**kwargs)

    @classmethod
    def parse_temporal_timestamp(cls, timestamp: str) -> str:
        """Convert temporal datetime strings into date strings.

        Invalid datetime strings are kept as-is."""
        temporal_date = None
        try:
            temporal_date = datetime_to_date(parse_datetime(timestamp)) or timestamp
        except (ValueError, TypeError):
            pass
        return temporal_date or timestamp

    def convert_license(self, license: dict) -> dict:
        ensure_dict(license)
        url = license.get("identifier")
        if not url:
            url = "http://uri.suomi.fi/codelist/fairdata/license/code/notspecified"
        return {
            "url": url,
            "custom_url": license.get("license", None),
            "description": license.get("description"),
        }

    def convert_access_rights(self) -> dict:
        access_rights = self.legacy_access_rights
        return {
            "license": [
                self.convert_license(v) for v in ensure_list(access_rights.get("license"))
            ],
            "description": access_rights.get("description", None),
            "access_type": self.convert_reference_data(AccessType, self.legacy_access_type),
            "restriction_grounds": [
                self.convert_reference_data(RestrictionGrounds, v)
                for v in ensure_list(access_rights.get("restriction_grounds"))
            ],
            "available": access_rights.get("available"),
        }

    def convert_data_catalog(self) -> Optional[DataCatalog]:
        if not self.legacy_data_catalog:
            return None

        if self.convert_only:
            try:
                return self.legacy_data_catalog.get("identifier")
            except AttributeError:
                pass
            return self.legacy_data_catalog

        catalog_id = self.legacy_data_catalog["identifier"]
        catalog, created = DataCatalog.objects.get_or_create(
            id=catalog_id, defaults={"title": {"und": catalog_id}}
        )
        if created:
            self.created_objects.update(["DataCatalog"])
        return catalog.id

    def get_or_create_reference_data(self, ref_data_model, url: str, defaults: dict) -> tuple:
        if self.convert_only:
            try:
                ref_data_model.objects.get(url=url)
            except ref_data_model.DoesNotExist:
                raise serializers.ValidationError(
                    f"{ref_data_model.__name__} not found with {url=}]"
                )

        instance, created = ref_data_model.objects.get_or_create(url=url, defaults={**defaults})
        if created:
            logger.info(
                f"Created reference data for {ref_data_model.__name__}: {dict(url=url, **defaults)}"
            )
        return instance, created

    def convert_reference_data(
        self, ref_data_model, concept: dict, pref_label_key="pref_label", defaults={}
    ) -> Optional[dict]:
        if not concept:
            return None
        ensure_dict(concept)
        instance, created = self.get_or_create_reference_data(
            ref_data_model=ref_data_model,
            url=concept["identifier"],
            defaults={
                "pref_label": concept.get(pref_label_key),
                "in_scheme": concept.get("in_scheme"),
                **defaults,  # Allow overriding defaults
            },
        )
        if created:
            self.created_objects.update([ref_data_model.__name__])
        return {"pref_label": instance.pref_label, "url": instance.url}

    def convert_spatial(self, spatial: dict) -> Optional[dict]:
        if not spatial:
            return None
        ensure_dict(spatial)
        location = None
        if location_data := spatial.get("place_uri"):
            location = self.convert_reference_data(Location, location_data)

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

    def convert_temporal(self, temporal: dict) -> Optional[dict]:
        if not temporal:
            return None
        ensure_dict(temporal)
        return {
            "start_date": self.parse_temporal_timestamp(temporal.get("start_date")),
            "end_date": self.parse_temporal_timestamp(temporal.get("end_date")),
            "temporal_coverage": temporal.get("temporal_coverage"),
        }

    def convert_other_identifier(self, other_identifier: dict) -> dict:
        ensure_dict(other_identifier)
        return {
            "notation": other_identifier.get("notation"),
            "identifier_type": self.convert_reference_data(
                IdentifierType, other_identifier.get("type")
            ),
        }

    def convert_homepage(self, homepage):
        if not homepage:
            return None
        ensure_dict(homepage)
        return {"title": homepage.get("title"), "url": homepage.get("identifier")}

    def ensure_refdata_organization(self, v3_organization: dict):
        """Create reference data organization if needed."""
        ensure_dict(v3_organization)
        url = v3_organization.get("url")
        parent_instance = None
        if parent := v3_organization.get("parent"):
            # Check that parent is also reference data
            parent_url = parent.get("url") or ""
            if parent_url.startswith(settings.ORGANIZATION_BASE_URI):
                parent_instance = Organization.objects.filter(
                    url=parent_url, is_reference_data=True
                ).first()
            if not parent_instance:
                raise serializers.ValidationError(
                    {
                        "is_part_of": (
                            f"Reference organization {url} cannot be "
                            f"child of non-reference organization {parent_url}"
                        )
                    }
                )

        # Create deprecated refdata organization if it does not exist
        _org, created = Organization.all_objects.get_or_create(
            url=url,
            is_reference_data=True,
            defaults={
                "pref_label": v3_organization.get("pref_label"),
                "in_scheme": settings.ORGANIZATION_SCHEME,
                "deprecated": timezone.now(),
                "parent": parent_instance,
            },
        )
        if created:
            self.created_objects.update(["Organization"])

    def convert_organization(self, organization: dict) -> dict:
        """Convert organization from V2 dict to V3 dict."""
        ensure_dict(organization)
        val = {
            "pref_label": organization.get("name"),
            "email": organization.get("email"),
            "homepage": self.convert_homepage(organization.get("homepage")),
        }

        parent = None
        if parent_data := organization.get("is_part_of"):
            parent = self.convert_organization(parent_data)
            val["parent"] = parent

        if identifier := organization.get("identifier"):
            if identifier.startswith(settings.ORGANIZATION_BASE_URI):
                val["url"] = identifier
                if not self.convert_only:
                    # Organization is reference data, make sure it exists
                    self.ensure_refdata_organization(val)
            else:
                val["external_identifier"] = identifier

        return val

    def convert_actor(self, actor: dict, roles=None) -> dict:
        """Convert actor from V2 dict (optionally with roles) to V3 dict."""
        ensure_dict(actor)
        val = {}
        typ = actor.get("@type")
        if typ == "Person":
            val["person"] = {
                "name": actor.get("name"),
                "external_identifier": actor.get("identifier"),
                "email": actor.get("email"),
            }
            if parent := actor.get("member_of"):
                val["organization"] = self.convert_organization(parent)
        elif typ == "Organization":
            val["organization"] = self.convert_organization(actor)
        else:
            raise serializers.ValidationError(
                {"actor": f"Unknown or missing actor @type value: {typ}."}
            )

        if roles:
            val["roles"] = roles  # Assign actor roles, not allowed for e.g. provenance actor
        return val

    def convert_actors(self) -> list:
        """Collect V2 actors from dataset and convert to V3 actor dicts."""
        actors_data = []  # list of dicts with actor as "actor" and list of roles as "roles"
        roles = ["creator", "publisher", "curator", "contributor", "rights_holder"]
        for role in roles:
            # Flatten actors list and add role data
            role_actors = self.legacy_research_dataset.get(role)
            if isinstance(role_actors, dict):
                role_actors = [role_actors]  # Publisher is dictionary instead of list
            role_actors = ensure_list(role_actors)
            for actor in role_actors:
                actor_match = None  # Combine identical actors if found
                for other in actors_data:
                    if other["actor"] == actor:
                        actor_match = other
                        actor_match["roles"].append(role)
                        break
                if not actor_match:
                    actors_data.append({"actor": actor, "roles": [role]})

        adapted = [
            self.convert_actor(actor["actor"], roles=actor["roles"]) for actor in actors_data
        ]
        return adapted

    def convert_checksum_v2_to_v3(self, checksum: dict, value_key="value") -> Optional[str]:
        if not checksum:
            return None
        ensure_dict(checksum)
        algorithm = checksum.get("algorithm", "").lower().replace("-", "")
        value = checksum.get(value_key, "").lower()
        return f"{algorithm}:{value}"

    def convert_concept(self, concept: dict) -> Optional[dict]:
        if not concept:
            return None
        ensure_dict(concept)
        return {
            "pref_label": concept.get("pref_label"),
            "definition": concept.get("definition"),
            "concept_identifier": concept.get("identifier"),
            "in_scheme": concept.get("in_scheme"),
        }

    def convert_variable(self, variable: dict) -> dict:
        ensure_dict(variable)
        return {
            "pref_label": variable.get("pref_label"),
            "description": variable.get("description"),
            "concept": self.convert_concept(variable.get("concept")),
            "universe": self.convert_concept(variable.get("universe")),
            "representation": variable.get("representation"),
        }

    def convert_provenance(self, provenance: dict) -> dict:
        ensure_dict(provenance)
        return {
            "title": provenance.get("title"),
            "description": provenance.get("description"),
            "outcome_description": provenance.get("outcome_description"),
            "spatial": self.convert_spatial(provenance.get("spatial")),
            "temporal": self.convert_temporal(provenance.get("temporal")),
            "event_outcome": self.convert_reference_data(
                EventOutcome, provenance.get("event_outcome")
            ),
            "lifecycle_event": self.convert_reference_data(
                LifecycleEvent, provenance.get("lifecycle_event")
            ),
            "variables": [
                self.convert_variable(var) for var in ensure_list(provenance.get("variable"))
            ],
            "is_associated_with": [
                self.convert_actor(actor)
                for actor in ensure_list(provenance.get("was_associated_with"))
            ],
        }

    def convert_entity(self, entity: dict) -> dict:
        ensure_dict(entity)
        return {
            "title": entity.get("title"),
            "description": entity.get("description"),
            "entity_identifier": entity.get("identifier"),
            "type": self.convert_reference_data(ResourceType, entity.get("type")),
        }

    def convert_relation(self, relation: dict) -> dict:
        ensure_dict(relation)
        return {
            "entity": self.convert_entity(relation.get("entity")),
            "relation_type": self.convert_reference_data(
                RelationType,
                relation.get("relation_type"),
                defaults={
                    "in_scheme": settings.LOCAL_REFERENCE_DATA_SOURCES["relation_type"]["scheme"]
                },
            ),
        }

    def convert_remote_resource(self, resource: dict) -> dict:
        ensure_dict(resource)
        title = None
        if v2_title := resource.get("title"):
            title = {"en": v2_title}

        description = None
        if v2_description := resource.get("description"):
            description = {"en": v2_description}

        use_category = None
        if v2_use_category := resource.get("use_category"):
            use_category = self.convert_reference_data(UseCategory, v2_use_category)

        file_type = None
        if v2_file_type := resource.get("file_type"):
            file_type = self.convert_reference_data(FileType, v2_file_type)

        access_url = (resource.get("access_url") or {}).get("identifier")
        download_url = (resource.get("download_url") or {}).get("identifier")

        return {
            "title": title,
            "description": description,
            "checksum": self.convert_checksum_v2_to_v3(
                resource.get("checksum"), value_key="checksum_value"
            ),
            "mediatype": resource.get("mediatype"),
            "use_category": use_category,
            "file_type": file_type,
            "access_url": access_url,
            "download_url": download_url,
        }

    def convert_project(self, project: dict) -> dict:
        ensure_dict(project)
        val = {
            "title": project.get("name"),
            "project_identifier": project.get("identifier"),
            "participating_organizations": [
                self.convert_organization(org)
                for org in ensure_list(project.get("source_organization"))
            ],
        }

        funder_type_data = []
        if funder_type := project.get("funder_type"):
            funder_type_data = self.convert_reference_data(FunderType, funder_type)
        funding_identifier = project.get("has_funder_identifier")
        val["funding"] = [
            {
                "funder": {
                    "organization": self.convert_organization(org),
                    "funder_type": funder_type_data,
                },
                "funding_identifier": funding_identifier,
            }
            for org in ensure_list(project.get("has_funding_agency"))
        ]
        return val

    def convert_root_level_fields(self):
        modified = None
        if modified_data := self.legacy_research_dataset.get("modified"):
            modified = modified_data
        elif modified_data := self.dataset_json.get("date_modified") or self.dataset_json.get(
            "date_created"
        ):
            modified = modified_data
        else:
            self.modified = self.created

        deprecated = None
        if self.dataset_json.get("deprecated"):
            # Use modification date for deprecation date if not already set
            deprecated = self.deprecated or self.modified

        last_modified_by = None
        if not self.convert_only:
            if user_modified := self.dataset_json.get("user_modified"):
                user, created = get_user_model().objects.get_or_create(username=user_modified)
                last_modified_by = user.id
                if created:
                    self.created_objects.update(["User"])

        fields = {
            "cumulation_started": self.dataset_json.get("date_cumulation_started"),
            "cumulation_ended": self.dataset_json.get("date_cumulation_ended"),
            "cumulative_state": self.dataset_json.get("cumulative_state"),
            "created": self.dataset_json.get("date_created"),
            "modified": modified,
            "deprecated": deprecated,
            "state": self.dataset_json.get("state"),
            "last_cumulative_addition": self.dataset_json.get("date_last_cumulative_addition"),
            "last_modified_by": last_modified_by,
        }
        return fields

    def convert_research_dataset_fields(self):
        """Convert simple research_dataset fields to v3 model"""
        issued = None
        if issued_data := self.legacy_research_dataset.get("issued"):
            issued = issued_data
        elif not self.issued and not self.convert_only:
            issued = datetime_to_date(self.modified)

        return {
            "persistent_identifier": self.legacy_persistent_identifier,
            "title": self.legacy_research_dataset.get("title"),
            "description": self.legacy_research_dataset.get("description"),
            "issued": issued,
            "keyword": self.legacy_research_dataset.get("keyword") or [],
        }

    def validate_identifiers(self):
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

    def convert_dataset(self):
        """Convert V2 dataset json to V3 json format.

        By default any missing reference data is created as deprecated
        entries. If LegacyDataset is initialized with convert_only=True,
        no reference data is created.
        """
        if not self.convert_only:
            self.validate_identifiers()

        root_level_fields = self.convert_root_level_fields()
        research_dataset_fields = self.convert_research_dataset_fields()
        rd = self.legacy_research_dataset
        data = {
            **root_level_fields,
            **research_dataset_fields,
            "data_catalog": self.convert_data_catalog(),
            "access_rights": self.convert_access_rights(),
            "actors": self.convert_actors(),
            "provenance": [self.convert_provenance(v) for v in ensure_list(rd.get("provenance"))],
            "projects": [self.convert_project(v) for v in ensure_list(rd.get("is_output_of"))],
            "field_of_science": [
                self.convert_reference_data(FieldOfScience, v)
                for v in ensure_list(rd.get("field_of_science"))
            ],
            "theme": [self.convert_reference_data(Theme, v) for v in ensure_list(rd.get("theme"))],
            "language": [
                self.convert_reference_data(
                    Language,
                    v,
                    pref_label_key="title",
                    defaults={
                        "in_scheme": settings.FINTO_REFERENCE_DATA_SOURCES["language"]["scheme"]
                    },
                )
                for v in ensure_list(rd.get("language"))
            ],
            "infrastructure": [
                self.convert_reference_data(ResearchInfra, v)
                for v in ensure_list(rd.get("infrastructure"))
            ],
            "spatial": [self.convert_spatial(v) for v in ensure_list(rd.get("spatial"))],
            "temporal": [self.convert_temporal(v) for v in ensure_list(rd.get("temporal"))],
            "other_identifiers": [
                self.convert_other_identifier(v) for v in ensure_list(rd.get("other_identifier"))
            ],
            "relation": [self.convert_relation(v) for v in ensure_list(rd.get("relation"))],
            "remote_resources": [
                self.convert_remote_resource(v) for v in ensure_list(rd.get("remote_resources"))
            ],
        }

        if self.convert_only:
            # Omit fields not in public serializer from response if
            # not doing actual data migration
            from apps.core.serializers.legacy_serializer import LegacyDatasetUpdateSerializer

            nonpublic = LegacyDatasetUpdateSerializer.Meta.nonpublic_fields
            data = {k: v for k, v in data.items() if k not in nonpublic}

        return data

    def attach_metadata_owner(self) -> Actor:
        """Creates new MetadataProvider object from metadata-owner field, that is usually CSC-username"""
        if self.convert_only:
            raise ValueError("Not supported with convert_only=True")

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

    def attach_contract(self) -> Contract:
        if self.convert_only:
            raise ValueError("Not supported with convert_only=True")
        if self.legacy_contract:
            ensure_dict(self.legacy_contract)
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

    def attach_files(self):
        if self.convert_only:
            raise ValueError("Not supported with convert_only=True")
        storage_file_objects = {}
        if files := self.files_json:
            ensure_list(files)
            for f in files:
                file_id = f["identifier"]
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

                storage_file_objects.setdefault(storage.id, []).append(new_file)

        file_set = None
        for storage_id, file_objects in storage_file_objects.items():
            file_set, created = FileSet.objects.get_or_create(dataset=self, storage_id=storage_id)
            if created:
                self.created_objects.update(["FileSet"])
            file_set.files.set(file_objects)
        return file_set

    def check_compatibility(self) -> Dict:
        v3_version = parse_iso_dates_in_nested_dict(copy.deepcopy(self.as_v2_dataset()))
        v2_version = parse_iso_dates_in_nested_dict(copy.deepcopy(self.dataset_json))
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

    def update_from_legacy(self, context=None):
        """Update dataset fields from legacy data dictionaries."""
        if not context:
            context = {}

        data = self.convert_dataset()
        from apps.core.serializers.legacy_serializer import LegacyDatasetUpdateSerializer

        self.saving_legacy = True  # Enable less strict validation on save
        serializer = LegacyDatasetUpdateSerializer(
            instance=self, data=data, context={**context, "dataset": self}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.attach_metadata_owner()
        self.attach_files()
        self.attach_contract()

        self.v2_dataset_compatibility_diff = self.check_compatibility()
        self.save()
        return self

    def save(self, *args, **kwargs):
        if self.convert_only:
            raise ValueError("Cannot save when convert_only=True")

        if str(self.id) != str(self.legacy_identifier):
            raise serializers.ValidationError({"id": _("Value does not match V2 identifier.")})

        self.validate_identifiers()

        if Dataset.objects.filter(id=self.id, legacydataset__isnull=True).exists():
            raise serializers.ValidationError(
                {"id": _("A non-legacy dataset already exists with the same identifier.")}
            )

        return super().save(*args, **kwargs)


def add_escapes(val: str):
    val = val.replace("[", "\\[")
    return val.replace("]", "\\]")
