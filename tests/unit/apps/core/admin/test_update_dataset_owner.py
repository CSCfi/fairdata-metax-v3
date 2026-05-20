import pytest
from django.urls import reverse

from apps.core import factories
from apps.core.models.catalog_record.meta import MetadataProvider
from apps.users.models import MetaxUser


@pytest.mark.django_db(databases=("default", "extra_connection"))
def test_admin_update_dataset_owner(admin_client, v2_integration_settings):
    user1 = MetaxUser.objects.create(username="user1")
    user2 = MetaxUser.objects.create(username="user2")
    new_user = MetaxUser.objects.create(username="new_owner")

    owner1 = MetadataProvider.objects.create(user=user1, organization="org1")
    owner2 = MetadataProvider.objects.create(
        user=user2, organization="org2", admin_organization="org2"
    )

    dataset1 = factories.PublishedDatasetFactory(metadata_owner=owner1)
    dataset2 = factories.PublishedDatasetFactory(metadata_owner=owner2)
    dataset3 = factories.PublishedDatasetFactory(metadata_owner=owner2)

    assert MetadataProvider.objects.count() == 2

    change_url = reverse("admin:core_dataset_changelist")

    def refresh():
        [dataset.refresh_from_db() for dataset in [dataset1, dataset2, dataset3]]

    data = {"action": "update_owner", "_selected_action": [dataset1.id, dataset2.id]}
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    body = response.content.decode()
    assert str(dataset1.id) in body
    assert str(dataset2.id) in body
    assert str(dataset3.id) not in body

    # Update user for dataset1 and dataset2
    data = {
        "action": "update_owner",
        "_selected_action": [dataset1.id, dataset2.id],
        "apply": 1,
        "user": str(new_user.id),
    }
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    refresh()
    assert dataset1.metadata_owner != owner1
    assert dataset1.metadata_owner.user == new_user
    assert dataset1.metadata_owner.organization == "org1"
    assert dataset1.metadata_owner.admin_organization is None

    assert dataset2.metadata_owner != owner2
    assert dataset2.metadata_owner.user == new_user
    assert dataset2.metadata_owner.organization == "org2"
    assert dataset2.metadata_owner.admin_organization == "org2"

    assert dataset3.metadata_owner == owner2
    assert dataset3.metadata_owner.organization == "org2"
    assert dataset3.metadata_owner.admin_organization == "org2"

    assert MetadataProvider.objects.count() == 4

    # Update organization for dataset1 and dataset2
    data = {
        "action": "update_owner",
        "_selected_action": [dataset1.id, dataset2.id],
        "apply": 1,
        "organization": "new_org",
    }
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    refresh()
    assert dataset1.metadata_owner != owner1
    assert dataset1.metadata_owner.user == new_user
    assert dataset1.metadata_owner.organization == "new_org"
    assert dataset1.metadata_owner.admin_organization is None

    assert dataset2.metadata_owner != owner2
    assert dataset2.metadata_owner.user == new_user
    assert dataset2.metadata_owner.organization == "new_org"
    assert dataset2.metadata_owner.admin_organization == "org2"

    assert dataset3.metadata_owner == owner2
    assert dataset3.metadata_owner.organization == "org2"
    assert dataset3.metadata_owner.admin_organization == "org2"

    assert MetadataProvider.objects.count() == 6

    # Update admin_organization for dataset1 and dataset2
    data = {
        "action": "update_owner",
        "_selected_action": [dataset1.id, dataset2.id],
        "apply": 1,
        "admin_organization": "new_org",
    }
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    refresh()
    assert dataset1.metadata_owner.user == new_user
    assert dataset1.metadata_owner.organization == "new_org"
    assert dataset1.metadata_owner.admin_organization == "new_org"

    assert dataset2.metadata_owner == dataset1.metadata_owner
    assert dataset2.metadata_owner.user == new_user
    assert dataset2.metadata_owner.organization == "new_org"
    assert dataset2.metadata_owner.admin_organization == "new_org"

    assert dataset3.metadata_owner == owner2
    assert dataset3.metadata_owner.user == user2
    assert dataset3.metadata_owner.organization == "org2"
    assert dataset3.metadata_owner.admin_organization == "org2"

    assert MetadataProvider.objects.count() == 7

    # Clear admin_organization for dataset1 and dataset2
    data = {
        "action": "update_owner",
        "_selected_action": [dataset1.id, dataset2.id],
        "apply": "Apply",
        "clear_admin_organization": 1,
    }
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    refresh()
    assert dataset1.metadata_owner.user == new_user
    assert dataset1.metadata_owner.organization == "new_org"
    assert dataset1.metadata_owner.admin_organization is None

    assert dataset2.metadata_owner == dataset1.metadata_owner
    assert dataset2.metadata_owner.user == new_user
    assert dataset2.metadata_owner.organization == "new_org"
    assert dataset2.metadata_owner.admin_organization is None

    assert dataset3.metadata_owner == owner2
    assert dataset3.metadata_owner.user == user2
    assert dataset3.metadata_owner.organization == "org2"
    assert dataset3.metadata_owner.admin_organization == "org2"

    assert MetadataProvider.objects.count() == 7

    # Set everything for all datasets
    data = {
        "action": "update_owner",
        "_selected_action": [dataset1.id, dataset2.id, dataset3.id],
        "apply": "Apply",
        "user": str(user1.id),
        "organization": "cool_organization",
        "admin_organization": "cool_admin_organization",
    }
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    refresh()
    assert dataset1.metadata_owner.user == user1
    assert dataset1.metadata_owner.organization == "cool_organization"
    assert dataset1.metadata_owner.admin_organization == "cool_admin_organization"

    assert dataset1.metadata_owner == dataset2.metadata_owner == dataset3.metadata_owner

    assert MetadataProvider.objects.count() == 8

    # Change nothing for all datasets
    data = {
        "action": "update_owner",
        "_selected_action": [dataset1.id, dataset2.id, dataset3.id],
        "apply": "Apply",
    }
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200

    refresh()
    assert dataset1.metadata_owner.user == user1
    assert dataset1.metadata_owner.organization == "cool_organization"
    assert dataset1.metadata_owner.admin_organization == "cool_admin_organization"

    assert dataset1.metadata_owner == dataset2.metadata_owner == dataset3.metadata_owner

    assert MetadataProvider.objects.count() == 8
