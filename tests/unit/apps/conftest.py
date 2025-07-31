from dataclasses import dataclass
from typing import Union
from uuid import UUID

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from knox.models import AuthToken
from rest_framework.reverse import reverse

from apps.core import factories
from apps.core.models import Dataset, AccessType
from apps.files.factories import create_project_with_files


@pytest.fixture
def data_urls():
    """Return urls related to dataset data."""

    def f(dataset: Union[Dataset, UUID, str]):
        dataset_id = dataset.id if isinstance(dataset, Dataset) else dataset
        kwargs = {"dataset_id": dataset_id}
        return {
            "dataset": reverse("dataset-detail", kwargs={"pk": dataset_id}),
            "files": reverse("dataset-files-list", kwargs=kwargs),
            "directories": reverse("dataset-directories-list", kwargs=kwargs),
        }

    return f


@pytest.fixture
def file_tree() -> dict:
    return create_project_with_files(
        file_paths=[
            "/dir1/file.csv",
            "/dir2/a.txt",
            "/dir2/b.txt",
            "/dir2/c.txt",
            "/dir2/subdir/file1.txt",
            "/dir2/subdir/file2.txt",
            "/dir3/file.pdf",
            "/rootfile.txt",
        ],
        file_args={"*": {"size": 1024}},
    )


@pytest.fixture
def deep_file_tree() -> dict:
    return create_project_with_files(
        file_paths=[
            "/dir1/file.csv",
            "/dir1/sub/file.csv",
            "/dir2/a.txt",
            "/dir2/subdir1/file1.txt",
            "/dir2/subdir1/file2.txt",
            "/dir2/subdir1/file3.txt",
            "/dir2/subdir2/file1.txt",
            "/dir2/subdir2/file2.txt",
            "/dir2/subdir2/file3.txt",
            "/dir2/subdir2/subsub/subsubsub1/file.txt",
            "/dir2/subdir2/subsub/subsubsub2/file1.txt",
            "/dir2/subdir2/subsub/subsubsub2/file2.txt",
            "/dir3/sub1/file.txt",
            "/dir3/sub2/file.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"size": 1024}},
    )


@pytest.fixture
def dataset_with_files(data_catalog, file_tree, access_type_reference_data):
    dataset = factories.DatasetFactory(
        data_catalog=data_catalog,
        persistent_identifier="somepid",
        access_rights__access_type=AccessType.objects.get(
            url="http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
        ),
    )
    dataset.access_rights.restriction_grounds.clear()
    factories.DatasetActorFactory(roles=["creator", "publisher"], dataset=dataset)
    storage = next(iter(file_tree["files"].values())).storage
    file_set = factories.FileSetFactory(dataset=dataset, storage=storage)
    file_set.files.set(
        [
            file_tree["files"]["/dir1/file.csv"],
            file_tree["files"]["/dir2/a.txt"],
            file_tree["files"]["/dir2/b.txt"],
            file_tree["files"]["/dir2/subdir/file1.txt"],
        ]
    )
    return dataset


@pytest.fixture
def dataset_with_files_metadata_requires_login(dataset_with_files, access_type_reference_data):
    dataset_with_files.access_rights = factories.AccessRightsFactory(
        show_file_metadata=False,
        access_type=AccessType.objects.get(
            url="http://uri.suomi.fi/codelist/fairdata/access_type/code/login"
        ),
        restriction_grounds=[
            factories.RestrictionGroundsFactory(
                url="http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/test"
            )
        ],
    )
    dataset_with_files.access_rights.save()
    dataset_with_files.publish()
    return dataset_with_files


@dataclass
class TokenUsers:
    user: get_user_model()
    token: str


@pytest.fixture
def end_users(faker, fairdata_users_group):
    user1 = get_user_model().objects.create(
        username=faker.simple_profile()["username"], password=faker.password(), organization="test"
    )
    user2 = get_user_model().objects.create(
        username=faker.simple_profile()["username"], password=faker.password(), organization="test"
    )
    user3 = get_user_model().objects.create(
        username=faker.simple_profile()["username"], password=faker.password(), organization="test"
    )
    fairdata_users_group.user_set.add(user1, user2, user3)
    instance1, token1 = AuthToken.objects.create(user=user1)
    instance2, token2 = AuthToken.objects.create(user=user2)
    instance3, token3 = AuthToken.objects.create(user=user3)
    return (
        TokenUsers(user=user1, token=token1),
        TokenUsers(user=user2, token=token2),
        TokenUsers(user=user3, token=token3),
    )


@pytest.fixture
def service_user(faker):
    group, _ = Group.objects.get_or_create(name="service")
    user = get_user_model().objects.create(
        username=faker.simple_profile()["username"], password=faker.password()
    )
    instance, token = AuthToken.objects.create(user=user)
    user.groups.add(group)
    return TokenUsers(user=user, token=token)


@pytest.fixture
def ida_service_user(service_user):
    group_ida, _ = Group.objects.get_or_create(name="ida")
    service_user.user.groups.add(group_ida)
    return service_user


@pytest.fixture
def update_request_client_auth_token():
    def _update_request_client_auth_token(client, token):
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    return _update_request_client_auth_token
