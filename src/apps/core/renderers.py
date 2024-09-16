import logging
from typing import Optional, Union

import shapely
from datacite import schema43
from django.db.models import Sum
from django.utils.translation import gettext as _
from jsonschema import exceptions as jsonschema_exceptions
from rest_framework import renderers, serializers

from apps.actors.models import Organization, Person
from apps.common.datacitedata import Datacitedata
from apps.common.helpers import deduplicate_list
from apps.core.models import Dataset, DatasetActor

logger = logging.getLogger(__file__)


class DataciteXMLRenderer(renderers.BaseRenderer, Datacitedata):
    """
    Renderer which serializes datasets to Datacite XML.
    """

    media_type = "application/xml"
    format = "datacite"
    strict = True  # enable validation with schema

    def validate_dataset(self, dataset: Dataset):
        """Check that dataset has all fields required by DataCite."""

        errors = {}

        identifier_type = (
            self.parse_identifier(
                dataset.persistent_identifier,
                value_field="identifier",
                type_field="identifierType",
            )
            or {}
        ).get("identifierType")
        if identifier_type != "DOI":
            errors["persistent_identifier"] = _("Dataset should have a DOI identifier.")

        for field in ["issued", "title"]:
            if not getattr(dataset, field, None):
                errors[field] = _("Value is required for DataCite.")

        roles = {
            role for actor in dataset.actors.all() for role in actor.roles
        }  # flatten lists of roles
        if missing_roles := {"creator", "publisher"} - roles:
            errors["actors"] = _("Missing required roles for DataCite: {roles}").format(
                roles=missing_roles
            )

        if errors:
            raise serializers.ValidationError(errors)

    def get_datacite_json(self, dataset: Dataset):
        """Create datacite json object."""
        datacite_json = self.get_mandatory_fields(dataset)

        ## Optional fields
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

        # TODO: The following optional fields are not implemented yet:
        # - formats
        # - version
        # - fundingReferences
        # - container
        # also missing:
        # - Project organization contributor (contributorType=ResearchGroup)

        if not self.strict:
            if not datacite_json["identifiers"]:
                # Support fairdata_datacite for draft dataset without persistent_identifier
                datacite_json["identifiers"] = [
                    {"identifier": str(dataset.id), "identifierType": "Metax dataset ID"}
                ]

        return datacite_json

    def render(self, data: Dataset, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.
        """
        if self.strict:
            self.validate_dataset(data)

        self.language = self.get_dataset_language(data)
        datacite_json = self.get_datacite_json(data)

        # Validate produced json
        if self.strict:
            try:
                schema43.validator.validate(datacite_json)
            except jsonschema_exceptions.ValidationError as error:
                raise serializers.ValidationError({error.json_path: error.message})

        # Generate DataCite XML from dictionary.
        doc = schema43.tostring(datacite_json)
        return doc.encode()


class FairdataDataciteXMLRenderer(DataciteXMLRenderer):
    """
    Renderer which serializes datasets to unvalidated Datacite XML.
    """

    format = "fairdata_datacite"
    strict = False
