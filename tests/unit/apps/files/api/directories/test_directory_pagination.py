import pytest

from tests.utils import assert_nested_subdict


@pytest.mark.django_db
def test_directory_pagination(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
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
                "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
                "directories": [
                    {"directory_name": "sub1"},
                    {"directory_name": "sub2"},
                    {"directory_name": "sub3"},
                    {"directory_name": "sub4"},
                    {"directory_name": "sub5"},
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
                "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
                "directories": [
                    {"directory_name": "sub6"},
                ],
                "files": [
                    {"file_name": "a.txt"},
                    {"file_name": "b.txt"},
                    {"file_name": "c.txt"},
                    {"file_name": "d.txt"},
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
                "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
                "directories": [],
                "files": [
                    {"file_name": "e.txt"},
                    {"file_name": "f.txt"},
                ],
            },
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_pagination_empty_due_to_offset(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
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
                "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
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
        "/rest/v3/directories",
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
                "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
                "directories": [],
                "files": [
                    {"file_name": "a.txt"},
                    {"file_name": "b.txt"},
                    {"file_name": "c.txt"},
                    {"file_name": "d.txt"},
                    {"file_name": "e.txt"},
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
                "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
                "directories": [],
                "files": [
                    {"file_name": "f.txt"},
                ],
            },
        },
        res.data,
        check_list_length=True,
    )
