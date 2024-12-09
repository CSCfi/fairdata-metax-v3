import json
import logging

import pytest
from pytest_bdd import given
from rest_framework.test import APIClient

logger = logging.getLogger(__name__)


@pytest.fixture
@given("the user has admin privileges")
def admin_client(admin_user):
    """

    Args:
        admin_user (): pytest-django fixture with admin privileges

    Returns:

    """
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def datacatalog_json():
    """

    Returns: json-object with DataCatalog POST-Request payload
    TODO:
        Should unify payload generation in tests

    """
    data = json.dumps(
        {
            "title": {"en": "Testing catalog", "fi": "Testi katalogi"},
            "language": [
                {
                    "url": "http://lexvo.org/id/iso639-3/fin",
                }
            ],
            "is_external": False,
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
            "dataset_versioning_enabled": False,
        }
    )
    return data
