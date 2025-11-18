import pytest
from rest_framework.exceptions import ValidationError

from apps.core.models.catalog_record import MetadataProvider

pytestmark = [pytest.mark.django_db]


def test_create_metadata_provider_with_user(user):
    metadata_provider = MetadataProvider(user=user)
    metadata_provider.save()
    assert metadata_provider.id is not None
    assert metadata_provider.user is not None
    assert metadata_provider.user == user


def test_delete_metadata_provider_with_foreign_keys(user):
    metadata_provider = MetadataProvider(user=user)
    metadata_provider.save()
    metadata_provider.delete()
    assert metadata_provider.removed
    assert user.removed is None


def test_change_metadata_provider_values(user, user2):
    metadata_provider = MetadataProvider.objects.create(
        user=user, organization="organization", admin_organization="admin_org"
    )
    metadata_provider.user = user2
    metadata_provider.organization = "other_organization"
    metadata_provider.admin_organization = "other_admin_org"
    with pytest.raises(ValidationError) as ec:
        metadata_provider.save()
    assert ec.value.detail == {
        "organization": "Value should not be changed for an existing instance",
        "user": "Value should not be changed for an existing instance",
        "admin_organization": "Value should not be changed for an existing instance",
    }
