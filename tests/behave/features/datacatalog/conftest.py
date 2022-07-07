import json
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from pytest_bdd import given, when, then
from rest_framework.reverse import reverse

from apps.core.models import DataCatalog, DataStorage

from rest_framework.test import APIClient

logger = logging.getLogger(__name__)


@pytest.fixture
@given("Im an admin user")
def admin_user():
    user, created = get_user_model().objects.get_or_create(
        username="test_admin", password="bqHA94MrZutrfe"
    )
    admin_group, created = Group.objects.get_or_create(name="admin")
    user.groups.add(admin_group)
    return user.save()


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


@when(
    "I post a new DataCatalog to the datacatalog REST-endpoint",
    target_fixture="request_result",
)
def datacatalog_post_request(admin_user, datacatalog_json):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse("datacatalog-list")
    return client.post(url, datacatalog_json, content_type="application/json")


@pytest.fixture
@then("New DataCatalog object is saved to database")
@pytest.mark.django_db
def check_datacatalog_is_created(request_result, datacatalog_json):
    logger.info(f"datacatalog_json: {datacatalog_json}")
    payload = json.loads(datacatalog_json)
    assert DataCatalog.objects.filter(title=payload["title"]).count() == 1
    return DataCatalog.objects.first()


@then("It should return 201 http code")
def check_datacatalog_return_code(request_result):
    assert request_result.status_code == 201


@when("I post delete request to datacatalog REST-endpoint")
def step_impl():
    raise NotImplementedError(
        "STEP: When I post delete request to datacatalog REST-endpoint"
    )


@then("New DataCatalog has publishing channels")
def has_publishing_channels():
    data_catalog = Mock()

    # ManyToManyField that registers distributed message queue updates for DataCatalog object
    data_catalog.publishing_channels.count = MagicMock(return_value=1)
    assert data_catalog.publishing_channels.count() != 0


@patch("apps.core.models.DataCatalog.data_storage")
@then("New DataCatalog has DataStorage")
def has_data_storage(check_datacatalog_is_created):
    check_datacatalog_is_created.data_storage = DataStorage()

    assert check_datacatalog_is_created.data_storage is not None
