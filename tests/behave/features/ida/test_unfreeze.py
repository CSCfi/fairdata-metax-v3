from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from pytest_bdd import scenario, then, when

from apps.core import factories
from apps.files.factories import FileFactory
from apps.files.models import File


@pytest.fixture
@when("user unfreezes file in IDA")
def user_unfreeze_request():
    request = MagicMock()
    request.status_code = 204
    yield request
    raise NotImplementedError


@pytest.fixture
@when("the file is marked as deleted")
def mark_files_deleted():
    file = FileFactory(date_frozen=timezone.now())
    dataset = factories.DatasetFactory()

    dataset.files.set([file])

    file.delete()

    return dataset, file.id


@pytest.fixture
@when("datasets with the deleted file are marked as deprecated")
def deprecate_dataset(mark_files_deleted):
    dataset, file_id = mark_files_deleted
    dataset.is_deprecated = True
    dataset.save()
    return dataset, file_id


@then("API returns OK-delete status")
def delete_ok(user_unfreeze_request):
    assert user_unfreeze_request.status_code == 204


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("file.feature", "IDA user unfreezes files")
def test_file_unfreeze(deprecate_dataset):
    dataset, file_id = deprecate_dataset
    assert dataset.is_deprecated is True
    assert File.available_objects.filter(id=file_id).count() == 0
