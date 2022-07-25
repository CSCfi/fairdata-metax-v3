import json
import logging

import pytest
from pytest_bdd import when, then, given, scenario
from rest_framework.reverse import reverse

from apps.core.models import DataCatalog

logger = logging.getLogger(__name__)


@when(
    "the user submits new data-catalog",
    target_fixture="datacatalog_post_request",
)
def datacatalog_post_request(admin_client, datacatalog_json):
    url = reverse("datacatalog-list")
    return admin_client.post(url, datacatalog_json, content_type="application/json")


@pytest.fixture
@when("new data-catalog is saved to database")
def check_datacatalog_is_created(datacatalog_post_request, datacatalog_json):
    logger.info(f"datacatalog_json: {datacatalog_json}")
    payload = json.loads(datacatalog_json)
    return DataCatalog.objects.get(title=payload["title"])


@then("the user should get an OK create-response")
def ok_create_response(datacatalog_post_request):
    assert datacatalog_post_request.status_code == 201


@pytest.mark.django_db
@scenario("datacatalog.feature", "Creating new data-catalog")
def test_datacatalog(datacatalog_json):
    payload = json.loads(datacatalog_json)
    assert DataCatalog.objects.filter(title=payload["title"]).count() == 1
