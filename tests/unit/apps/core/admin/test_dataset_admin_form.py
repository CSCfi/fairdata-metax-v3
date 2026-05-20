import pytest

from apps.core import factories
from apps.core.admin import DatasetAdminForm
from apps.core.models.catalog_record.meta import MetadataProvider
from apps.users.models import MetaxUser

pytestmark = [pytest.mark.django_db(databases=("default", "extra_connection"))]


@pytest.fixture
def dataset():
    user = MetaxUser.objects.create(username="user")
    owner = MetadataProvider.objects.create(
        user=user, organization="org", admin_organization="admin_org"
    )
    return factories.PublishedDatasetFactory(metadata_owner=owner)


def test_form_initial_values(dataset):
    form = DatasetAdminForm(instance=dataset)

    assert form.initial["metadata_owner_user"] == dataset.metadata_owner.user
    assert form.initial["metadata_owner_organization"] == "org"
    assert form.initial["metadata_owner_admin_organization"] == "admin_org"


def test_form_save(mocker, dataset):
    new_user = MetaxUser.objects.create(username="new_owner")

    # Use initial values as base data so form has all required fields
    initial_data = DatasetAdminForm(instance=dataset).initial
    form_data = {
        **initial_data,
        "metadata_owner_user": new_user.id,
        "metadata_owner_organization": "new org",
        "metadata_owner_admin_organization": "new admin org",
    }

    form = DatasetAdminForm(instance=dataset, data=form_data)
    old_owner = dataset.metadata_owner

    assert form.is_valid(), form.errors
    assert MetadataProvider.objects.count() == 1
    saved = form.save()
    assert MetadataProvider.objects.count() == 2

    assert saved.metadata_owner != old_owner
    assert saved.metadata_owner.user.username == "new_owner"
    assert saved.metadata_owner.organization == "new org"
    assert saved.metadata_owner.admin_organization == "new admin org"

    # Old MetadataProvider should be unchanged
    assert old_owner.user.username == "user"
    assert old_owner.organization == "org"
    assert old_owner.admin_organization == "admin_org"


def test_form_requires_owner_and_organization(dataset):
    initial_data = DatasetAdminForm(instance=dataset).initial
    form_data = {
        **initial_data,
        "metadata_owner_user": None,
        "metadata_owner_organization": None,
        "metadata_owner_admin_organization": None,
    }

    form = DatasetAdminForm(instance=dataset, data=form_data)

    assert not form.is_valid()
    assert form.errors == {
        "metadata_owner_user": ["This field is required."],
        "metadata_owner_organization": ["This field is required."],
    }


def test_form_can_empty_admin_organization(dataset):
    initial_data = DatasetAdminForm(instance=dataset).initial
    form_data = {
        **initial_data,
        "metadata_owner_admin_organization": None,
    }

    form = DatasetAdminForm(instance=dataset, data=form_data)
    assert form.is_valid()
    saved = form.save()
    assert saved.metadata_owner.user.username == "user"
    assert saved.metadata_owner.organization == "org"
    assert saved.metadata_owner.admin_organization == None
