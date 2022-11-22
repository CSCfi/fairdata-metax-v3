import logging

import pytest
from pytest_bdd import scenario, when, then

from apps.core.factories import DatasetFactory

logger = logging.getLogger(__name__)

@pytest.fixture
@when("user saves a draft of unpublished dataset in Qvain")
def qvain_draft_request(mock_qvain_dataset_with_files_request, recwarn):
    yield mock_qvain_dataset_with_files_request(status_code=201, published=False)
    raise NotImplementedError


@pytest.fixture
@when("new unpublished dataset is created without persistent identifier")
def created_draft():
    dataset = DatasetFactory(
        persistent_identifier=None,
    )
    yield dataset
    raise NotImplementedError


@then("the dataset exists in draft state")
def is_draft_dataset(created_draft):
    logger.info(__name__)
    assert created_draft.persistent_identifier is None
    assert created_draft.issued is None


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Saving draft of unpublished Dataset")
def test_dataset_draft(qvain_draft_request):
    assert qvain_draft_request.status_code == 201
