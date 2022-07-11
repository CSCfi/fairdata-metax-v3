from unittest.mock import MagicMock

import pytest
from django.forms import model_to_dict
from django.utils import timezone
from pytest_bdd import when, then, scenario

from apps.core import factories
from apps.core.models import File


@when("User unfreezes file in IDA")
def user_unfreeze_request():
    request = MagicMock()
    request.status_code = 200
    return request


@pytest.fixture
@then("The file is marked as deleted")
def mark_files_deleted():
    file = factories.FileFactory(date_frozen=timezone.now())
    factories.DistributionFactory(files=[file])
    file_id = file.id

    distributions = file.distribution_set.all()
    datasets = [x.dataset for x in distributions]
    file.delete()

    assert File.available_objects.filter(id=file_id).count() == 0

    return datasets


@then("Any Dataset with the file is marked as deprecated")
def deprecate_dataset(mark_files_deleted):
    for dataset in mark_files_deleted:
        dataset.is_deprecated = True
        dataset.save()
    for dataset in mark_files_deleted:
        assert dataset.is_deprecated is True


@pytest.mark.django_db
@scenario("file.feature", "IDA user unfreezes files")
def test_file_unfreeze():
    assert True
