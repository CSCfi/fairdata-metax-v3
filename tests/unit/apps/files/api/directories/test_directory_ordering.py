import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.file]

def test_directory_ordering_name(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["name"] for d in res.data["directories"]]
    assert names == ["sub1", "sub2", "sub3", "sub4", "sub5", "sub6"]


def test_directory_ordering_name_reverse(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "-name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["name"] for d in res.data["directories"]]
    assert names == ["sub6", "sub5", "sub4", "sub3", "sub2", "sub1"]


def test_directory_ordering_size(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "size",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["name"] for d in res.data["directories"]]
    assert names == ["sub2", "sub3", "sub4", "sub6", "sub5", "sub1"]


def test_directory_ordering_multiple(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "-file_count,name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["name"] for d in res.data["directories"]]
    assert names == ["sub1", "sub5", "sub2", "sub3", "sub4", "sub6"]


def test_file_ordering_name(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "file_ordering": "filename",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["filename"] for d in res.data["files"]]
    assert names == ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt", "f.txt"]


def test_file_ordering_name_reverse(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "file_ordering": "-filename",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["filename"] for d in res.data["files"]]
    assert names == ["f.txt", "e.txt", "d.txt", "c.txt", "b.txt", "a.txt"]


def test_file_ordering_path(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "file_ordering": "pathname",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["filename"] for d in res.data["files"]]
    assert names == ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt", "f.txt"]
