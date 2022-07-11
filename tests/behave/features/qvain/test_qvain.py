import pytest
from pytest_bdd import scenario


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Publishing new version from dataset")
def test_dataset_new_version():
    assert True
