import pytest
from tests.utils import matchers

from apps.core import factories
from apps.files import factories as filefactories
from apps.users.models import MetaxUser

pytestmark = [pytest.mark.django_db, pytest.mark.file]


@pytest.fixture
def published_dataset(file_tree_a):
    dataset = factories.PublishedDatasetFactory(persistent_identifier="somepid")
    factories.FileSetFactory(
        dataset=dataset,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/b.txt"],
            file_tree_a["files"]["/dir/c.txt"],
        ],
    )
    return dataset


@pytest.fixture
def draft_dataset(file_tree_a):
    dataset = factories.DatasetFactory(persistent_identifier="draft:somepid")
    dataset.actors.add(factories.DatasetActorFactory(roles=["creator", "publisher"]))
    factories.FileSetFactory(
        dataset=dataset,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/d.txt"],
        ],
    )
    return dataset


def test_files_list_published(admin_client, file_tree_a, published_dataset, draft_dataset):
    # Draft does not count towards published files
    res = admin_client.get(
        "/v3/files",
        {**file_tree_a["params"], "published": True},
        content_type="application/json",
    )
    assert [f.get("published") for f in res.data["results"]] == [matchers.DateTimeStr()] * 3

    # Draft has 1 not already published file
    admin_client.post(f"/v3/datasets/{draft_dataset.id}/publish")
    res = admin_client.get(
        "/v3/files",
        {**file_tree_a["params"], "published": True},
        content_type="application/json",
    )
    assert [f.get("published") for f in res.data["results"]] == [matchers.DateTimeStr()] * 4

    # Files get unpublished when all linked published datasets are removed
    admin_client.delete(f"/v3/datasets/{published_dataset.id}?flush=true")
    res = admin_client.get(
        "/v3/files",
        {**file_tree_a["params"], "published": True},
        content_type="application/json",
    )
    assert [f.get("published") for f in res.data["results"]] == [matchers.DateTimeStr()] * 2

    # Check non-published files are listed properly
    res = admin_client.get(
        "/v3/files",
        {**file_tree_a["params"], "published": False},
        content_type="application/json",
    )
    assert [f.get("published") for f in res.data["results"]] == [None] * 14

    # Delete file so dataset will be deprecated and the remaining file is unpublished
    admin_client.delete(f'/v3/files/{file_tree_a["files"]["/dir/a.txt"].id}')
    res = admin_client.get(
        "/v3/files",
        {**file_tree_a["params"], "published": True},
        content_type="application/json",
    )
    assert res.data["results"] == []
