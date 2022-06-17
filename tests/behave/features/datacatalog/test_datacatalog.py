import pytest
from pytest_bdd import scenario


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("datacatalog.feature", "Creating new DataCatalog")
def test_datacatalog():
    assert True
