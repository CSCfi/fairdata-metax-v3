import pytest
from pytest_bdd import scenario, given, then, when
from rest_framework.reverse import reverse
from apps.core import factories
from apps.core.models import DataCatalog


@given("there is an existing data-catalog", target_fixture="data_catalog")
def exists_datacatalog():
    return factories.DataCatalogFactory()

@when("the user removes the data-catalog", target_fixture="request_result")
def remove_datacatalog(data_catalog, admin_client):
    url = reverse("datacatalog-detail", kwargs={'id': data_catalog.id})
    response = admin_client.delete(url)
    return response


@then("the data-catalog is soft deleted")
def soft_delete_datacatalog(data_catalog):
    assert DataCatalog.available_objects.filter(id=data_catalog.id).count() == 0
    assert DataCatalog.all_objects.filter(id=data_catalog.id).count() == 1


@then("the user should get an OK delete-response")
def ok_delete_response(request_result):
    assert request_result.status_code == 204


@pytest.mark.django_db
@scenario("datacatalog.feature", "Deleting data-catalog")
def test_delete_datacatalog():
    assert True
