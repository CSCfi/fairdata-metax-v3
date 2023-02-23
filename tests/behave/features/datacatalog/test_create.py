import json
import logging

import pytest
from pytest_bdd import given, scenario, then, when
from rest_framework.reverse import reverse

from apps.core.models import DataCatalog

logger = logging.getLogger(__name__)


@pytest.fixture
@when("the user submits new data-catalog")
def datacatalog_post_request(admin_client, datacatalog_json, reference_data):
    """

    Args:
        admin_client (): Authenticated admin client
        datacatalog_json (): JSON-body for new data-catalog

    Returns: Response object

    """
    url = reverse("datacatalog-list")
    return admin_client.post(url, datacatalog_json, content_type="application/json")


@pytest.fixture
@when("new data-catalog is saved to database")
def datacatalog_from_post_request(datacatalog_post_request, datacatalog_json) -> DataCatalog:
    """

    Args:
        datacatalog_post_request (): POST-request to datacatalog-api
        datacatalog_json (): POST-request body used to load instance from database

    Returns:
         DataCatalog: instance created from POST-request

    """
    logger.info(f"datacatalog_json: {datacatalog_json}")
    payload = json.loads(datacatalog_json)
    return DataCatalog.objects.get(title=payload["title"])


@then("the user should get an OK create-response")
def is_response_create_ok(datacatalog_post_request):
    """

    Args:
        datacatalog_post_request (): POST-request to datacatalog-api


    """
    assert datacatalog_post_request.status_code == 201


@scenario("datacatalog.feature", "Creating new data-catalog")
@pytest.mark.django_db
def test_datacatalog(datacatalog_json, datacatalog_from_post_request):
    """

    Args:
        datacatalog_json (): POST-request body, used for assert validation

    """
    assert datacatalog_from_post_request is not None
