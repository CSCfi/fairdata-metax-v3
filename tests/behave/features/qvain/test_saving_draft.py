import pytest
from pytest_bdd import scenario, when, then

from apps.core.factories import ResearchDatasetFactory


@pytest.fixture
@when("user saves a draft of unpublished dataset in Qvain")
def qvain_draft_request(mock_qvain_dataset_with_files_request):
    return mock_qvain_dataset_with_files_request(status_code=201, published=False)


@pytest.fixture
@when("new unpublished dataset is created without persistent identifier")
def create_draft(faker):
    dataset = ResearchDatasetFactory(
        persistent_identifier=None,
    )
    return dataset


@then("the dataset exists in draft state")
def is_draft_dataset(create_draft):
    assert create_draft.persistent_identifier is None
    assert create_draft.release_date is None


@pytest.mark.django_db
@scenario("dataset.feature", "Saving draft of unpublished Dataset")
def test_dataset_draft(qvain_draft_request):
    assert qvain_draft_request.status_code == 201
