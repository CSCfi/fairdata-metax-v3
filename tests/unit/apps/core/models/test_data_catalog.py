import pytest
from unittest.mock import patch
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

from apps.core import factories

pytestmark = [pytest.mark.django_db]


def test_create_data_catalog_with_foreign_keys(data_catalog):
    assert data_catalog.id is not None


def test_delete_data_catalog_with_foreign_keys(data_catalog):
    publisher = data_catalog.publisher
    language = data_catalog.language
    data_catalog.delete()
    assert publisher.catalogs.filter(id=data_catalog.id).count() == 0
    # assert language.filter(catalogs__id=data_catalog_with_foreign_keys.id).count() == 0


def test_data_catalog_managed_pid_types(data_catalog):
    data_catalog.allowed_pid_types = ["URN", "DOI", "external"]
    data_catalog.save()
    assert data_catalog.managed_pid_types == ["URN", "DOI"]


class TestCanCreateDatasets:
    """Tests for DataCatalog.can_create_datasets method."""

    def test_can_create_datasets_caches_result(self):
        """Test that can_create_datasets caches the result for the same user."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        user = MetaxUser.objects.create_user(username="test_user", email="test@example.com")

        # Mock _can_create_datasets to track calls
        with patch.object(catalog, "_can_create_datasets", return_value=True) as mock_method:
            # First call should invoke _can_create_datasets
            result1 = catalog.can_create_datasets(user)
            assert result1 is True
            assert mock_method.call_count == 1

            # Second call should use cache, not call _can_create_datasets again
            result2 = catalog.can_create_datasets(user)
            assert result2 is True
            assert mock_method.call_count == 1  # Still 1, not 2

    def test_can_create_datasets_different_users_have_separate_cache_entries(self):
        """Test that different users have separate cache entries."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        user1 = MetaxUser.objects.create_user(username="user1", email="user1@example.com")
        user2 = MetaxUser.objects.create_user(username="user2", email="user2@example.com")

        # Mock _can_create_datasets to return different values
        def mock_can_create(user):
            return user.username == "user1"

        with patch.object(catalog, "_can_create_datasets", side_effect=mock_can_create):
            result1 = catalog.can_create_datasets(user1)
            result2 = catalog.can_create_datasets(user2)

            assert result1 is True
            assert result2 is False

            # Verify both users are in cache
            assert user1.id in catalog._create_user_cache
            assert user2.id in catalog._create_user_cache
            assert catalog._create_user_cache[user1.id] is True
            assert catalog._create_user_cache[user2.id] is False

    def test_can_create_datasets_user_with_group_in_dataset_groups_create(self):
        """Test that user with group in dataset_groups_create can create datasets."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        group = Group.objects.create(name="test_group")
        catalog.dataset_groups_create.set([group])

        user = MetaxUser.objects.create_user(username="test_user", email="test@example.com")
        user.groups.set([group])

        assert catalog.can_create_datasets(user) is True

    def test_can_create_datasets_user_without_group_cannot_create(self):
        """Test that user without group in dataset_groups_create cannot create datasets."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        group = Group.objects.create(name="test_group")
        catalog.dataset_groups_create.set([group])

        user = MetaxUser.objects.create_user(username="test_user", email="test@example.com")
        # User is not in the group

        assert catalog.can_create_datasets(user) is False

    def test_can_create_datasets_superuser_can_always_create(self):
        """Test that superuser can always create datasets regardless of groups."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        # Catalog has no groups set
        catalog.dataset_groups_create.set([])

        superuser = MetaxUser.objects.create_user(
            username="superuser", email="super@example.com", is_superuser=True
        )

        assert catalog.can_create_datasets(superuser) is True

    def test_can_create_datasets_empty_dataset_groups_create(self):
        """Test that catalog with empty dataset_groups_create allows no regular users."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        catalog.dataset_groups_create.set([])

        user = MetaxUser.objects.create_user(username="test_user", email="test@example.com")

        assert catalog.can_create_datasets(user) is False

    def test_can_create_datasets_user_in_multiple_groups(self):
        """Test that user in one of the allowed groups can create datasets."""
        MetaxUser = get_user_model()
        catalog = factories.DataCatalogFactory()
        group1 = Group.objects.create(name="group1")
        group2 = Group.objects.create(name="group2")
        catalog.dataset_groups_create.set([group1, group2])

        user = MetaxUser.objects.create_user(username="test_user", email="test@example.com")
        user.groups.set([group1])  # User is only in group1

        assert catalog.can_create_datasets(user) is True
