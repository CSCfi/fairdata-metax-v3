import pytest
from pytest_bdd import scenario, given, then, when
from rest_framework.reverse import reverse
from apps.core import factories
from apps.core.models import DataCatalog


@given("there is an existing data-catalog", target_fixture="data_catalog")
def exists_datacatalog() -> DataCatalog:
    """

    Returns:
        DataCatalog: New data-catalog instance

    """
    return factories.DataCatalogFactory()


@when("the user removes the data-catalog", target_fixture="datacatalog_delete_request")
def remove_datacatalog(data_catalog, admin_client):
    """

    Args:
        data_catalog (DataCatalog): Data-catalog used as kwarg for detail-view
        admin_client (): Authenticated admin client

    Returns: Response object

    """
    url = reverse("datacatalog-detail", kwargs={"id": data_catalog.id})
    response = admin_client.delete(url)
    return response


@then("the data-catalog is soft deleted")
def is_datacatalog_soft_deleted(data_catalog):
    """

    Args:
        data_catalog (DataCatalog): Deleted data-catalog instance

    """
    assert DataCatalog.available_objects.filter(id=data_catalog.id).count() == 0
    assert DataCatalog.all_objects.filter(id=data_catalog.id).count() == 1


@then("the user should get an OK delete-response")
def is_response_delete_ok(datacatalog_delete_request):
    """

    Args:
        datacatalog_delete_request (): Response object from DELETE-request

    """
    assert datacatalog_delete_request.status_code == 204


@pytest.mark.django_db
@scenario("datacatalog.feature", "Deleting data-catalog")
def test_delete_datacatalog():
    assert True
