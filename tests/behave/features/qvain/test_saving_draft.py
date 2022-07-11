import pytest
from pytest_bdd import scenario, when, then


@when("user saves a draft of unpublished dataset in Qvain")
def qvain_draft_request(mock_qvain_dataset_with_files_request):
    return mock_qvain_dataset_with_files_request(status_code=201, published=False)


@then("new unpublished dataset is created without persistent identifier")
def step_impl():
    raise NotImplementedError(u"STEP: Then New Research Dataset is saved to database")


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Saving draft of unpublished Dataset")
def test_dataset_draft():
    assert True
