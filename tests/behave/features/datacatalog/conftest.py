import json
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from pytest_bdd import scenario, given, when, then
from django.urls import reverse

from apps.core.models import DataCatalog

from rest_framework.test import APIClient


@pytest.fixture
@given("Im an admin user")
def admin_user():
    user, created = get_user_model().objects.get_or_create(username='test_admin', password='bqHA94MrZutrfe')
    admin_group, created = Group.objects.get_or_create(name="admin")
    user.groups.add(admin_group)
    return user.save()


@pytest.fixture
def datacatalog_json():
    data = json.dumps(
        {
            "title": {
                "en": "Testing catalog",
                "fi": "Testi katalogi"
            },
            "language": [
                {
                    "title": {
                        "en": "Finnish",
                        "fi": "suomi",
                        "sv": "finska",
                        "und": "suomi"
                    },
                    "id": "http://lexvo.org/id/iso639-3/fin"
                }]
            ,
            "harvested": False,
            "publisher": {
                "name": {
                    "en": "Testing",
                    "fi": "Testi"
                },
                "homepage": [{
                    "title": {
                        "en": "Publisher organization website",
                        "fi": "Julkaisijaorganisaation kotisivu"
                    },
                    "id": "http://www.testi.fi/"
                }]

            },
            "id": "urn:nbn:fi:att:data-catalog-testi",
            "access_rights": {
                "license":
                    {
                        "title": {
                            "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                            "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                            "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)"
                        },
                        "id": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
                    }
                ,
                "access_type":
                    {
                        "id": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
                        "title": {
                            "en": "Open",
                            "fi": "Avoin",
                            "und": "Avoin"
                        }
                    }
                ,
                "description": {
                    "en": "Contains datasets from Repotronic service",
                    "fi": "Sisältää aineistoja Repotronic-palvelusta"
                }
            },
            "dataset_versioning_enabled": False,
            "research_dataset_schema": "att"
        }
    )
    return data


@when("I post a new DataCatalog to the datacatalog REST-endpoint", target_fixture="request_result")
def datacatalog_post_request(admin_user, datacatalog_json):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse('datacatalog')
    return client.post(url, datacatalog_json, content_type='application/json')


@then("New DataCatalog object is saved to database")
@pytest.mark.django_db
def check_datacatalog_is_created(request_result):
    assert DataCatalog.objects.all().count() == 1


@then("It should return 201 http code")
def check_datacatalog_return_code(request_result):
    assert request_result.status_code == 201


@when("I post delete request to datacatalog REST-endpoint")
def step_impl():
    raise NotImplementedError(u'STEP: When I post delete request to datacatalog REST-endpoint')


@then("New DataCatalog has publishing channels")
def step_impl():
    pass


@then("New DataCatalog has DataStorage")
def step_impl():
    pass
