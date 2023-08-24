import pytest
from tests.utils import assert_nested_subdict


@pytest.mark.django_db
def test_directory_pagination(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "limit": 5,
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert "offset=5" in res.data["next"]
    assert_nested_subdict(
        {
            "count": 12,
            "previous": None,
            "results": {
                "directory": {"file_count": 15, "size": 15 * 1024},
                "directories": [
                    {"name": "sub1"},
                    {"name": "sub2"},
                    {"name": "sub3"},
                    {"name": "sub4"},
                    {"name": "sub5"},
                ],
                "files": [],
            },
        },
        res.data,
        check_list_length=True,
    )

    res = client.get(res.data["next"])
    assert res.status_code == 200
    assert "offset" not in res.data["previous"]
    assert "offset=10" in res.data["next"]
    assert_nested_subdict(
        {
            "count": 12,
            "results": {
                "directory": {"file_count": 15, "size": 15 * 1024},
                "directories": [
                    {"name": "sub6"},
                ],
                "files": [
                    {"filename": "a.txt"},
                    {"filename": "b.txt"},
                    {"filename": "c.txt"},
                    {"filename": "d.txt"},
                ],
            },
        },
        res.data,
        check_list_length=True,
    )

    res = client.get(res.data["next"])
    assert res.status_code == 200
    assert "offset=5" in res.data["previous"]
    assert_nested_subdict(
        {
            "count": 12,
            "next": None,
            "results": {
                "directory": {"file_count": 15, "size": 15 * 1024},
                "directories": [],
                "files": [
                    {"filename": "e.txt"},
                    {"filename": "f.txt"},
                ],
            },
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_pagination_empty_due_to_offset(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "offset": 10000,
            "limit": 5,
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "count": 12,
            "results": {
                "directory": {"file_count": 15, "size": 15 * 1024},
                "directories": [],
                "files": [],
            },
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_pagination_with_name(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "path": "/dir",
            "limit": 5,
            "name": ".txt",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert "offset=5" in res.data["next"]
    assert_nested_subdict(
        {
            "count": 6,
            "previous": None,
            "results": {
                "directory": {"file_count": 15, "size": 15 * 1024},
                "directories": [],
                "files": [
                    {"filename": "a.txt"},
                    {"filename": "b.txt"},
                    {"filename": "c.txt"},
                    {"filename": "d.txt"},
                    {"filename": "e.txt"},
                ],
            },
        },
        res.data,
        check_list_length=True,
    )

    res = client.get(res.data["next"])
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "count": 6,
            "next": None,
            "results": {
                "directory": {"file_count": 15, "size": 15 * 1024},
                "directories": [],
                "files": [
                    {"filename": "f.txt"},
                ],
            },
        },
        res.data,
        check_list_length=True,
    )
