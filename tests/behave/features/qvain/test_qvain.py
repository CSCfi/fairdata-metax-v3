import pytest
from pytest_bdd import scenario


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario('dataset.feature', 'Publishing new dataset')
def test_dataset_publish():
    assert True


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario('dataset.feature', 'Saving draft of unpublished Dataset')
def test_dataset_draft():
    assert True


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario('dataset.feature', 'Publishing new version from dataset')
def test_dataset_new_version():
    assert True
