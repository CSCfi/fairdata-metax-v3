import copy
import logging
import re
from collections import Counter
from typing import Optional, Tuple

import shapely.wkt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.actors.models import Organization
from apps.common.helpers import (
    datetime_to_date,
    ensure_dict,
    ensure_list,
    is_valid_float_str,
    is_valid_url,
    omit_empty,
    process_nested,
    quote_url,
    remove_wkt_point_duplicates,
)

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
    PreservationEvent,
    RelationType,
    ResearchInfra,
    ResourceType,
    RestrictionGrounds,
    Theme,
    UseCategory,
)
from .data_catalog import DataCatalog

logger = logging.getLogger(__name__)


def add_escapes(val: str):
    val = val.replace("[", "\\[")
    return val.replace("]", "\\]")


def regex(path: str):
    """Escape [ and ] and compile into regex."""
    return re.compile(add_escapes(path))


class LegacyDatasetConverter:
    """Adapter for converting V2 dataset json to V3 style dataset json."""

    def __init__(self, *args, dataset_json, convert_only=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_objects = Counter()

        # Operate on copy of dataset_json so we can do some extra
        # annotations in the nested dict without modifying the original.
        self.dataset_json = copy.deepcopy(dataset_json)

        # When convert_only is enabled, no related reference data objects are created.
        self.convert_only = convert_only

    @property
    def legacy_research_dataset(self):
        return ensure_dict(self.dataset_json.get("research_dataset") or {})

    @property
    def legacy_access_rights(self):
        return ensure_dict(self.legacy_research_dataset.get("access_rights") or {})

    @property
    def legacy_data_catalog(self):
        return self.dataset_json.get("data_catalog")

    def mark_invalid(self, obj: dict, error: str, fields=[]):
        """Mark object as being invalid."""
        already_exists = "_invalid" in obj
        entry = obj.setdefault("_invalid", {})
        entry.update(
            {
                "value": {k: v for k, v in obj.items() if not k.startswith("_")},
                "error": error,
            }
        )

        if fields:
            # Add fields to existing ones if any
            if not already_exists or "fields" in entry:
                entry.setdefault("fields", []).extend(fields)
        else:
            # Remove fields key to indicate entire object is bad
            entry.pop("fields", None)
        obj["_invalid"] = entry

    def mark_fixed(self, obj: dict, error: str, fields=[], fixed_value=None):
        """Mark object as having fixed values for fields."""
        entry = {
            "value": {k: v for k, v in obj.items() if not k.startswith("_")},
            "error": error,
        }
        if fields:
            entry["fields"] = fields
        if fixed_value:
            entry["fixed_value"] = fixed_value
        obj["_fixed"] = entry

    def fix_url(self, url: str) -> Tuple[Optional[str], bool]:
        if not url:
            return None, False
        url = url.strip()  # Remove whitespace

        if not (url.startswith("http://") or url.startswith("https://")):
            return url, False  # Not a URL

        old_url = url
        # Fix e.g. spaces inside urls
        url = quote_url(url)
        # Fix https://zenodo.org123 -> https://zenodo.org/records/123
        url = re.sub("https://zenodo.org([\d]+)$", r"https://zenodo.org/records/\1", url)

        return url, url != old_url

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
            "title": license.get("title"),
            "description": license.get("description"),
        }

    def convert_access_rights(self) -> dict:
        access_rights = self.legacy_access_rights
        return {
            "license": [
                self.convert_license(v) for v in ensure_list(access_rights.get("license"))
            ],
            "description": access_rights.get("description", None),
            "access_type": self.convert_reference_data(
                AccessType, access_rights.get("access_type")
            ),
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
            url=concept.get("identifier"),
            defaults={
                "pref_label": concept.get(pref_label_key),
                "in_scheme": concept.get("in_scheme"),
                "deprecated": timezone.now(),
                **defaults,  # Allow overriding defaults
            },
        )
        if created:
            self.created_objects.update([ref_data_model.__name__])
        return {"pref_label": instance.pref_label, "url": instance.url}

    def is_valid_wkt(self, wkt: str):
        try:
            shapely.wkt.loads(wkt)
        except shapely.errors.GEOSException:
            return False
        return True

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
            "altitude_in_meters": spatial.get("alt"),
        }
        if (alt := spatial.get("alt")) and not is_valid_float_str(alt):
            self.mark_invalid(spatial, error="Invalid number", fields=["alt"])

        if spatial.get("as_wkt"):
            # Remove invalid entries from as_wkt
            as_wkt = spatial.get("as_wkt", [])
            valid_wkt = []
            for wkt in as_wkt:
                if self.is_valid_wkt(wkt):
                    valid_wkt.append(wkt)

            if len(valid_wkt) != len(as_wkt):
                self.mark_invalid(spatial, error="Invalid WKT", fields=["as_wkt"])

            if (
                len(valid_wkt) == 1
                and location
                and (
                    location_wkt := (
                        Location.objects.filter(url=location.get("url"))
                        .values_list("as_wkt", flat=True)
                        .first()
                    )
                )
            ):
                valid_wkt = remove_wkt_point_duplicates(location_wkt, valid_wkt)

            obj["custom_wkt"] = valid_wkt or None

        return obj

    def convert_temporal(self, temporal: dict) -> Optional[dict]:
        if not temporal:
            return None
        ensure_dict(temporal)
        start_date = self.parse_temporal_timestamp(temporal.get("start_date"))
        end_date = self.parse_temporal_timestamp(temporal.get("end_date"))
        if start_date and end_date and end_date < start_date:
            start_date, end_date = end_date, start_date
            self.mark_fixed(
                temporal, error="End date after start date", fields=["start_date", "end_date"]
            )
        return {
            "start_date": start_date,
            "end_date": end_date,
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
        parent = v3_organization.get("parent")
        if parent:
            # Check that parent is also reference data
            parent_url = parent.get("url") or ""
            if parent_url.startswith(settings.ORGANIZATION_BASE_URI):
                parent_instance = Organization.objects.filter(
                    url=parent_url, is_reference_data=True
                ).first()

        org = Organization.all_objects.filter(url=url, is_reference_data=True).first()
        if org:
            # Use parent from existing organization. This avoids errors from
            # reference data organizations that have invalid parent data.
            v3_organization.pop("parent", None)
        else:
            # Create deprecated refdata org
            if parent and not parent_instance:
                raise serializers.ValidationError(
                    {
                        "is_part_of": (
                            f"Reference organization {url} cannot be "
                            f"child of non-reference organization {parent_url}"
                        )
                    }
                )
            Organization.all_objects.create(
                url=url,
                is_reference_data=True,
                pref_label=v3_organization.get("pref_label"),
                in_scheme=settings.ORGANIZATION_SCHEME,
                deprecated=timezone.now(),
                parent=parent_instance,
            )
            self.created_objects.update(["Organization"])

    def convert_organization(self, organization: dict) -> Optional[dict]:
        """Convert organization from V2 dict to V3 dict."""
        if not organization:
            return None
        val = {
            "pref_label": organization.get("name"),
            "email": organization.get("email"),
            "homepage": self.convert_homepage(organization.get("homepage")),
        }

        parent = None
        if parent_data := organization.get("is_part_of"):
            parent = self.convert_organization(parent_data)
            val["parent"] = parent

        identifier, fixed = self.fix_url(organization.get("identifier"))
        if fixed:
            self.mark_fixed(
                organization, error="Invalid URL", fields=["identifier"], fixed_value=identifier
            )
        if identifier:
            if identifier.startswith(settings.ORGANIZATION_BASE_URI):
                val["url"] = identifier
                if not self.convert_only:
                    # Organization is reference data, make sure it exists
                    self.ensure_refdata_organization(val)
            else:
                val["external_identifier"] = identifier

        if not val.get("url") and not omit_empty(val.get("pref_label", {})):
            self.mark_invalid(organization, error="Invalid organization")
            return None

        return val

    def convert_actor(self, actor: dict, roles=None) -> Optional[dict]:
        """Convert actor from V2 dict (optionally with roles) to V3 dict."""
        ensure_dict(actor)
        val = {}
        typ = actor.get("@type")
        v2_org = None
        if typ == "Person":
            val["person"] = {
                "name": actor.get("name"),
                "external_identifier": actor.get("identifier"),
                "email": actor.get("email"),
                "homepage": self.convert_homepage(actor.get("homepage")),
            }
            if parent := actor.get("member_of"):
                v2_org = parent
        elif typ == "Organization":
            v2_org = actor
        else:
            raise serializers.ValidationError(
                {"actor": f"Unknown or missing actor @type value: {typ}."}
            )

        if v2_org:
            val["organization"] = self.convert_organization(v2_org)
            if v2_org.get("_invalid"):
                self.mark_invalid(actor, error="Invalid actor")
                return None

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
                        actor_match["duplicates"].append(actor)
                        break
                if not actor_match:
                    actors_data.append({"actor": actor, "roles": [role], "duplicates": []})

        adapted = []
        for actor in actors_data:
            adapted_actor = self.convert_actor(actor["actor"], roles=actor["roles"])
            if adapted_actor:
                adapted.append(adapted_actor)
            for dup in actor["duplicates"]:
                # Actor may have been annotated, copy values to its duplicates
                dup.update(copy.deepcopy(actor["actor"]))

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
        identifier = concept.get("identifier")
        if identifier and not is_valid_url(identifier):
            self.mark_invalid(concept, error="Invalid URL")
            return None
        in_scheme = concept.get("in_scheme")
        if in_scheme and not is_valid_url(in_scheme):
            self.mark_invalid(concept, error="Invalid URL")
            return None
        return {
            "pref_label": concept.get("pref_label"),
            "definition": concept.get("definition"),
            "concept_identifier": identifier,
            "in_scheme": in_scheme,
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
            "preservation_event": self.convert_reference_data(
                PreservationEvent, provenance.get("preservation_event")
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

    def convert_remote_url(self, url_data: dict) -> Optional[str]:
        if not url_data:
            return None

        url = url_data.get("identifier")
        if not url:
            return None
        url, fixed = self.fix_url(str(url))
        if not is_valid_url(url):
            self.mark_invalid(url_data, error="Invalid URL")
            return None
        if fixed:
            self.mark_fixed(url_data, error="Invalid URL", fields=["identifier"], fixed_value=url)
        return url

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

        access_url = self.convert_remote_url(resource.get("access_url"))
        download_url = self.convert_remote_url(resource.get("download_url"))

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

        funder_type_data = None
        if funder_type := project.get("funder_type"):
            funder_type_data = self.convert_reference_data(FunderType, funder_type)
        funding_identifier = project.get("has_funder_identifier")
        funding_agencies = ensure_list(project.get("has_funding_agency")) or [None]
        val["funding"] = omit_empty(
            [
                {
                    "funder": {
                        "organization": self.convert_organization(org),
                        "funder_type": funder_type_data,
                    },
                    "funding_identifier": funding_identifier,
                }
                for org in funding_agencies
            ],
            recurse=True,
        )
        return val

    def get_modified(self):
        return (
            self.legacy_research_dataset.get("modified")
            or self.dataset_json.get("date_modified")
            or self.dataset_json.get("date_created")
        )

    def convert_root_level_fields(self):
        modified = self.get_modified()

        deprecated = None
        if self.dataset_json.get("deprecated"):
            date_deprecated = self.dataset_json.get("date_deprecated")
            # Use modification date for deprecation date if not already set
            deprecated = date_deprecated or modified

        last_modified_by = None
        if not self.convert_only:
            if user_modified := self.dataset_json.get("user_modified"):
                user, created = get_user_model().objects.get_or_create(username=user_modified)
                last_modified_by = user.id
                if created:
                    self.created_objects.update(["User"])

        fields = {
            "data_catalog": self.convert_data_catalog(),
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

        if not self.convert_only:
            fields["api_version"] = self.dataset_json.get("api_meta", {}).get("version", 1)

        if self.dataset_json.get("use_doi_for_published"):
            fields["pid_type"] = "DOI"
        return fields

    def convert_research_dataset_fields(self):
        """Convert simple research_dataset fields to v3 model"""
        issued = None
        if issued_data := self.legacy_research_dataset.get("issued"):
            issued = issued_data
        elif not self.convert_only:
            issued = datetime_to_date(parse_datetime(self.get_modified()))

        return {
            "persistent_identifier": self.legacy_research_dataset.get("preferred_identifier"),
            "title": self.legacy_research_dataset.get("title"),
            "description": self.legacy_research_dataset.get("description"),
            "issued": issued,
            "keyword": self.legacy_research_dataset.get("keyword") or [],
            "bibliographic_citation": self.legacy_research_dataset.get("bibliographic_citation"),
        }

    def convert_dataset(self):
        """Convert V2 dataset json to V3 json format.

        Any missing reference data is created as deprecated entries.
        """
        root_level_fields = self.convert_root_level_fields()

        rd = self.legacy_research_dataset
        research_dataset = {
            **self.convert_research_dataset_fields(),
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

        data = {**root_level_fields, **omit_empty(research_dataset, recurse=True)}

        if self.convert_only:
            # Omit fields not in public serializer from response if
            # not doing actual data migration
            from apps.core.serializers.legacy_serializer import LegacyDatasetUpdateSerializer

            nonpublic = LegacyDatasetUpdateSerializer.Meta.nonpublic_fields
            data = {k: v for k, v in data.items() if k not in nonpublic}

        return data

    def get_invalid_values_by_path(self):
        """Get invalid legacy values organized by dotted path."""
        invalid_by_path = {}

        def handler(value, path):
            if isinstance(value, dict) and (inv := value.get("_invalid")):
                invalid_by_path[path] = inv
                return None  # no need to go deeper
            return value

        process_nested(self.legacy_research_dataset, pre_handler=handler, path="research_dataset")
        return invalid_by_path or None

    def get_fixed_values_by_path(self) -> Optional[dict]:
        """Get fixed legacy values organized by dotted path."""
        fixed_values_by_path = {}

        def handler(value, path):
            if isinstance(value, dict) and (fix := value.get("_fixed")):
                fixed_values_by_path[path] = fix
            return value

        process_nested(self.legacy_research_dataset, post_handler=handler, path="research_dataset")
        return fixed_values_by_path or None
