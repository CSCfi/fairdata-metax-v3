import pytest


@pytest.mark.django_db
def test_directory_ordering_name(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "directory_name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["directory_name"] for d in res.data["directories"]]
    assert names == ["sub1", "sub2", "sub3", "sub4", "sub5", "sub6"]


@pytest.mark.django_db
def test_directory_ordering_name_reverse(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "-directory_name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["directory_name"] for d in res.data["directories"]]
    assert names == ["sub6", "sub5", "sub4", "sub3", "sub2", "sub1"]


@pytest.mark.django_db
def test_directory_ordering_byte_size(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "byte_size",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["directory_name"] for d in res.data["directories"]]
    assert names == ["sub2", "sub3", "sub4", "sub6", "sub5", "sub1"]


@pytest.mark.django_db
def test_directory_ordering_multiple(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "directory_ordering": "-file_count,directory_name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["directory_name"] for d in res.data["directories"]]
    assert names == ["sub1", "sub5", "sub2", "sub3", "sub4", "sub6"]


@pytest.mark.django_db
def test_file_ordering_name(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "file_ordering": "file_name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["file_name"] for d in res.data["files"]]
    assert names == ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt", "f.txt"]


@pytest.mark.django_db
def test_file_ordering_name_reverse(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "file_ordering": "-file_name",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["file_name"] for d in res.data["files"]]
    assert names == ["f.txt", "e.txt", "d.txt", "c.txt", "b.txt", "a.txt"]


@pytest.mark.django_db
def test_file_ordering_path(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "path": "/dir",
            "pagination": False,
            "file_ordering": "file_path",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    names = [d["file_name"] for d in res.data["files"]]
    assert names == ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt", "f.txt"]
