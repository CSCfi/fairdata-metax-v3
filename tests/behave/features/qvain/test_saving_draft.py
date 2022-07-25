import pytest
from django.utils import timezone
from pytest_bdd import scenario, when, then

from apps.core.factories import ResearchDatasetFactory


@when("user saves a draft of unpublished dataset in Qvain")
def qvain_draft_request(mock_qvain_dataset_with_files_request):
    return mock_qvain_dataset_with_files_request(status_code=201, published=False)


@when("new unpublished dataset is created without persistent identifier")
def create_draft(faker):
    dataset = ResearchDatasetFactory(
        release_date=timezone.now(),
        persistent_identifier=faker.uuid4(),
    )


@pytest.mark.django_db
@scenario("dataset.feature", "Saving draft of unpublished Dataset")
def test_dataset_draft():
    assert True
