import logging
from typing import Optional, Union

import shapely
from django.db.models import Sum

from apps.actors.models import Organization, Person
from apps.common.helpers import deduplicate_list
from apps.core.models import Dataset, DatasetActor

logger = logging.getLogger(__file__)


class InvalidCoordinates(ValueError):
    """Invalid latitude or longitude."""


def remove_duplicates(lst: list) -> list:
    """Remove duplicate values from list."""
    new_lst = []
    for item in lst:
        if not any(added == item for added in new_lst):
            new_lst.append(item)
    return new_lst


class Datacitedata:

    language = None  # 2-character language code

    # Map languages to 2-character codes
    language_codes = {
        "http://lexvo.org/id/iso639-3/eng": "en",
        "http://lexvo.org/id/iso639-3/fin": "fi",
        "http://lexvo.org/id/iso639-3/swe": "sv",
    }

    # Identify identifier type by prefix
    identifier_prefix_to_type = {
        "https://doi.org/10.": "DOI",
        "http://doi.org/10.": "DOI",
        "doi:10.": "DOI",
        "10.": "DOI",
        "urn:": "URN",
        "http://": "URL",
        "https://": "URL",
    }

    role_to_datacite_contributor_type = {
        "curator": "DataCurator",
        "contributor": "Other",
        "rights_holder": "RightsHolder",
    }

    # Relationship of resource being registered (A) and related resource (B), e.g. "A Cites B"
    relation_to_datacite_relation_type = {
        "http://purl.org/spar/cito/cites": "Cites",
        "http://purl.org/spar/cito/citesForInformation": "Cites",
        "http://purl.org/spar/cito/isCitedBy": "IsCitedBy",
        "http://purl.org/vocab/frbr/core#isSupplementTo": "IsSupplementTo",
        "http://purl.org/dc/terms/relation": None,
        "http://purl.org/vocab/frbr/core#successorOf": None,
        "http://purl.org/dc/terms/hasPart": "HasPart",
        "http://purl.org/dc/terms/isPartOf": "IsPartOf",
        "http://www.w3.org/ns/prov#wasDerivedFrom": "IsDerivedFrom",
        "purl.org/spar/cito/isCompiledBy": "IsCompiledBy",
        "http://purl.org/vocab/frbr/core#alternate": "IsVariantFormOf",
        "http://www.w3.org/2002/07/owl#sameAs": "IsIdenticalTo",
        "http://www.w3.org/ns/adms#previous": "IsNewVersionOf",  # A link to previous version
        "http://www.w3.org/ns/adms#next": "IsPreviousVersionOf",  # A link to next version
    }

    # Identifier types listed here are normalized to use common prefix
    identifier_type_output_prefix = {"DOI": "10."}

    @property
    def language_order(self):
        """Order in which languages should be prioritized when a single translation is needed."""
        order = ["en", "fi", "sv", "und"]
        if self.language:
            order.insert(0, self.language)
            order = deduplicate_list(order)
        return order

    def translate(self, value: dict) -> Optional[str]:
        """Return single translation value for multilanguage dict."""
        if not value:
            return value

        for lang in self.language_order + list(value):
            if translation := value.get(lang):
                return translation
        return None

    def translate_to_dict(self, value: dict, value_field: str, lang_field="lang") -> dict:
        """Return translation value and lang for multilanguage dict."""
        if not value:
            return {}

        translation_value = None
        translation_lang = None
        for lang in self.language_order + list(value):
            if translation_value := value.get(lang):
                translation_lang = lang
                break

        if not translation_value:
            return {}

        if translation_lang == "und":
            translation_lang = None
        return {value_field: translation_value, lang_field: translation_lang}

    def parse_identifier(
        self, identifier: str, value_field: str, type_field: str, as_list=False, default_type=None
    ) -> Union[dict, list]:
        """Determine type of identifier and normalize it.

        Returns dict with identifier value and type in fields
        determined by `value_field` and `type_field`.

        If as_list is enabled, the return value is a list
        with one or zero items.
        """
        identifier_value = identifier
        identifier_prefix = ""
        identifier_type = None
        if identifier:
            # Find first match from identifier_prefix_to_type
            for prefix, typ in self.identifier_prefix_to_type.items():
                if identifier.lower().startswith(prefix):
                    identifier_type = typ
                    identifier_value = identifier[len(prefix) :]
                    identifier_prefix = self.identifier_type_output_prefix.get(typ) or prefix
                    break

        # Use default identifier type if provided
        if not identifier_type:
            identifier_type = default_type

        value = None
        if identifier_value and identifier_type:
            # Return identifier only if its type is known
            value = {
                value_field: identifier_prefix + identifier_value,
                type_field: identifier_type,
            }

        if as_list:
            return [v for v in [value] if value]
        return value

    def person_to_datacite(self, person: Person):
        return {
            "name": person.name,
            "nameType": "Personal",
            "nameIdentifiers": self.parse_identifier(
                person.external_identifier,
                value_field="nameIdentifier",
                type_field="nameIdentifierScheme",
                as_list=True,
            ),
        }

    def organization_to_datacite(self, org: Organization):
        return {
            **self.translate_to_dict(org.pref_label, value_field="name"),  # name and lang
            "nameType": "Organizational",
            "nameIdentifiers": self.parse_identifier(
                org.external_identifier,
                value_field="nameIdentifier",
                type_field="nameIdentifierScheme",
                as_list=True,
            ),
        }

    def affiliation(self, org: Organization):
        while org.parent:
            org = org.parent
        return [{"name": self.translate(org.pref_label)}]

    def actor_to_datacite(self, actor: DatasetActor, contributor_type=None):
        if person := actor.person:
            datacite_actor = self.person_to_datacite(person)
            if parent_org := actor.organization:
                datacite_actor["affiliation"] = self.affiliation(parent_org)
        elif org := actor.organization:
            datacite_actor = self.organization_to_datacite(org)
            if parent_org := org.parent:
                datacite_actor["affiliation"] = self.affiliation(parent_org)

        if contributor_type:
            datacite_actor["contributorType"] = contributor_type
        return datacite_actor

    def get_dataset_language(self, dataset: Dataset) -> Optional[str]:
        for lang in dataset.language.all():
            if code := self.language_codes.get(lang.url):
                return code
        return None

    def flatten_geometry(self, geometry):
        """Flatten multipart geometries like MultiPolygon into separate parts."""
        if geometry.geom_type in {"MultiPolygon", "GeometryCollection"}:
            geometries = []
            subgeometries = shapely.get_parts(geometry)
            for sg in subgeometries:
                geometries.extend(self.flatten_geometry(sg))
        else:
            geometries = [geometry]
        return geometries

    def _coords_to_datacite(self, x, y):
        if not (-180 <= x <= 180):
            raise InvalidCoordinates(f"Longitude {x} is not in range [-180, 180].")
        if not (-90 <= y <= 90):
            raise InvalidCoordinates(f"Latitude {y} is not in range [-90, 90].")
        return {
            "pointLongitude": str(x),
            "pointLatitude": str(y),
        }

    def get_geometries_point(self, geometries: shapely.Geometry) -> Optional[dict]:
        """Return up to one point from flattened geometries."""
        for geometry in geometries:
            # DataCite supports only one point per location
            if geometry.geom_type == "Point":
                try:
                    return self._coords_to_datacite(geometry.x, geometry.y)
                except InvalidCoordinates as e:
                    logger.warning(f"Skipping invalid point: {e}")
                    continue
        return None

    def get_geometries_polygons(self, geometries: shapely.Geometry) -> list:
        """Return polygons from flattened geometries."""
        polygons = []
        for geometry in geometries:
            # DataCite supports only polygon exterior, no holes
            if geometry.geom_type == "Polygon":
                try:
                    polygons.append(
                        {
                            "polygonPoints": [
                                self._coords_to_datacite(x, y) for x, y in geometry.exterior.coords
                            ]
                        }
                    )
                except InvalidCoordinates as e:
                    logger.warning(f"Skipping polygon with invalid point: {e}")
                    continue
        return polygons

    def get_wkt_data(self, wkt_list: list) -> dict:
        """Parse WKT and return polygons and points."""
        wkt_data = {}
        geometries = []
        for wkt in wkt_list:
            geometries = []
            try:
                geometry = shapely.wkt.loads(wkt)
                geometries.extend(self.flatten_geometry(geometry))

            except shapely.errors.GEOSException as error:
                logger.warning(f"Invalid WKT, skipping: {error}")

            if point := self.get_geometries_point(geometries):
                wkt_data["geoLocationPoint"] = point
            if polygons := self.get_geometries_polygons(geometries):
                wkt_data["geoLocationPolygons"] = polygons

        return wkt_data

    def get_geolocations(self, dataset: Dataset) -> list:
        geolocations = []
        for spatial in dataset.spatial.all():
            location = {}
            if spatial.geographic_name:
                location["geoLocationPlace"] = spatial.geographic_name

            wkt_list = spatial.custom_wkt or []
            if reference_wkt := spatial.reference and spatial.reference.as_wkt:
                wkt_list.append(reference_wkt)

            location.update(self.get_wkt_data(wkt_list))
            if location:
                geolocations.append(location)

        return geolocations

    def get_dates(self, dataset: Dataset):
        dates = []

        if issued := dataset.issued:
            dates.append({"date": str(issued), "dateType": "Issued"})

        for temporal in dataset.temporal.all():
            start_date = temporal.start_date
            end_date = temporal.end_date
            if start_date and end_date:
                dates.append({"date": f"{start_date}/{end_date}", "dateType": "Other"})
            elif start_date:
                dates.append({"date": str(start_date), "dateType": "Other"})
            elif end_date:
                dates.append({"date": str(end_date), "dateType": "Other"})

        if access_rights := dataset.access_rights:
            if (
                access_rights.access_type
                and access_rights.access_type.url
                == "http://uri.suomi.fi/codelist/fairdata/access_type/code/embargo"
            ):
                if available := access_rights.available:
                    dates.append({"date": str(available), "dateType": "Available"})
        return dates

    def get_mandatory_fields(self, dataset: Dataset):
        publication_year = None
        if issued := dataset.issued:
            publication_year = str(issued.year)
        else:
            publication_year = str(dataset.created.year)

        datacite_json = {
            "identifiers": self.parse_identifier(
                dataset.persistent_identifier,
                value_field="identifier",
                type_field="identifierType",
                as_list=True,
            ),
            "titles": [{"lang": lang, "title": title} for lang, title in dataset.title.items()],
            "creators": [
                self.actor_to_datacite(actor)
                for actor in dataset.actors.filter(roles__contains=["creator"])
            ],
            # Publisher is a string and there can be only one publisher
            "publisher": next(
                (
                    self.actor_to_datacite(actor)["name"]
                    for actor in dataset.actors.filter(roles__contains=["publisher"])
                ),
                None,
            ),
            "publicationYear": publication_year,
            "types": {
                "resourceTypeGeneral": "Dataset",  # Resource type from controlled list
                "resourceType": "Dataset",  # Free-form resource type string
            },
            "schemaVersion": "http://datacite.org/schema/kernel-4",
        }
        return datacite_json

    def get_descriptions(self, dataset: Dataset):
        return [
            {"description": description, "descriptionType": "Abstract", "lang": lang}
            for lang, description in (dataset.description or {}).items()
        ]

    def get_contributors(self, dataset: Dataset):
        contributors = []
        for role, contributor_type in self.role_to_datacite_contributor_type.items():
            contributors.extend(
                [
                    self.actor_to_datacite(actor, contributor_type=contributor_type)
                    for actor in dataset.actors.filter(roles__contains=[role])
                ]
            )
        return contributors

    def get_related_identifiers(self, dataset: Dataset):
        related_identifiers = []

        # Add other identifiers
        for identifier in dataset.other_identifiers.all():
            parsed = self.parse_identifier(
                identifier.notation,
                value_field="relatedIdentifier",
                type_field="relatedIdentifierType",
                default_type="URL",
            )
            if parsed:
                parsed["relationType"] = "IsIdenticalTo"
                related_identifiers.append(parsed)

        # Map relation types to relation types
        for relation in dataset.relation.all():
            identifier = relation.entity.entity_identifier
            relation_type = self.relation_to_datacite_relation_type.get(relation.relation_type.url)
            # DataCite requires both identifier and relation type
            if identifier and relation_type:
                parsed = self.parse_identifier(
                    identifier,
                    value_field="relatedIdentifier",
                    type_field="relatedIdentifierType",
                    default_type="URL",
                )
                if parsed:
                    parsed["relationType"] = relation_type
                    related_identifiers.append(parsed)
        return related_identifiers

    def get_subjects(self, data):
        """Add theme, field of science and keyword data to subjects."""
        subjects = []
        for subject in list(data.theme.all()) + list(data.field_of_science.all()):
            subjects.extend(
                [
                    {
                        "subject": translation,
                        "valueUri": subject.url,
                        "schemeUri": subject.in_scheme,
                        "lang": lang,
                    }
                    for lang, translation in subject.pref_label.items()
                ]
            )
        subjects.extend([{"subject": keyword} for keyword in data.keyword])
        return subjects

    def get_rights_list(self, dataset: Dataset):
        if not dataset.access_rights:
            return []

        rights = []
        for license in dataset.access_rights.license.all():
            url = license.custom_url or license.reference.url
            title = license.description or license.reference.pref_label
            rights.extend(
                [
                    {
                        "rights": translation,
                        "lang": lang,
                        "rightsUri": url,
                    }
                    for lang, translation in title.items()
                ]
            )
        return rights

    def get_sizes(self, dataset):
        """Unstructured size information about the resource."""
        sizes = []
        if fileset := getattr(dataset, "file_set", None):  # Byte size of fileset
            if size := fileset.files.aggregate(size=Sum("size")).get("size"):
                sizes.append(f"{size} bytes")
        return sizes

    def get_datacite_json(self, dataset):
        """Create datacite json object."""

        datacite_json = self.get_mandatory_fields(dataset)

        # Optional fields
        datacite_json["descriptions"] = self.get_descriptions(dataset)
        if self.language:
            datacite_json["language"] = self.language
        datacite_json["contributors"] = self.get_contributors(dataset)
        datacite_json["dates"] = self.get_dates(dataset)
        datacite_json["relatedIdentifiers"] = self.get_related_identifiers(dataset)
        datacite_json["subjects"] = self.get_subjects(dataset)
        datacite_json["geoLocations"] = self.get_geolocations(dataset)
        datacite_json["rightsList"] = self.get_rights_list(dataset)
        datacite_json["sizes"] = self.get_sizes(dataset)

        # Remove duplicates to prevent validation errors
        for field in datacite_json:
            value = datacite_json[field]
            if isinstance(value, list):
                datacite_json[field] = remove_duplicates(value)

        return datacite_json
