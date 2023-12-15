from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from pytest_bdd import scenario, then, when

from apps.core import factories
from apps.core.models import FileSet
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
    file = FileFactory(frozen=timezone.now())
    dataset = factories.DatasetFactory()
    file_set = FileSet.objects.create(dataset=dataset, storage=file.storage)
    file_set.files.set([file])

    file.delete()

    return dataset, file.id


@pytest.fixture
@when("datasets with the deleted file are marked as deprecated")
def deprecate_dataset(mark_files_deleted):
    dataset, file_id = mark_files_deleted
    dataset.deprecated = timezone.now()
    dataset.save()
    return dataset, file_id


@then("API returns OK-delete status")
def delete_ok(user_unfreeze_request):
    assert user_unfreeze_request.status_code == 204


@pytest.mark.xfail(raises=NotImplementedError)
@scenario("file.feature", "IDA user unfreezes files")
@pytest.mark.django_db
def test_file_unfreeze(deprecate_dataset):
    dataset, file_id = deprecate_dataset
    assert dataset.deprecated is not None
    assert File.available_objects.filter(id=file_id).count() == 0
