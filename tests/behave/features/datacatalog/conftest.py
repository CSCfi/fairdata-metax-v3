import json
import logging

import pytest

from pytest_bdd import given

from rest_framework.test import APIClient

logger = logging.getLogger(__name__)


@pytest.fixture
@given("the user has admin privileges")
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def datacatalog_json():
    """

    Returns: json-object with DataCatalog POST-Request payload
    TODO: Should unify payload generation in tests

    """
    data = json.dumps(
        {
            "title": {"en": "Testing catalog", "fi": "Testi katalogi"},
            "language": [
                {
                    "title": {
                        "en": "Finnish",
                        "fi": "suomi",
                        "sv": "finska",
                        "und": "suomi",
                    },
                    "url": "http://lexvo.org/id/iso639-3/fin",
                }
            ],
            "harvested": False,
            "publisher": {
                "name": {"en": "Testing", "fi": "Testi"},
                "homepage": [
                    {
                        "title": {
                            "en": "Publisher organization website",
                            "fi": "Julkaisijaorganisaation kotisivu",
                        },
                        "url": "http://www.testi.fi/",
                    }
                ],
            },
            "id": "urn:nbn:fi:att:data-catalog-testi",
            "access_rights": {
                "license": {
                    "title": {
                        "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                        "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                        "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                    },
                    "url": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
                },
                "access_type": {
                    "url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
                    "title": {"en": "Open", "fi": "Avoin", "und": "Avoin"},
                },
                "description": {
                    "en": "Contains datasets from Repotronic service",
                    "fi": "Sisältää aineistoja Repotronic-palvelusta",
                },
            },
            "dataset_versioning_enabled": False,
            "research_dataset_schema": "att",
        }
    )
    return data
