import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.file]


def test_directory_include_parent_true(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "include_parent": False,
            "path": "/dir",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert "parent_directory" not in res.data


def test_directory_include_parent_false(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "include_parent": False,
            "path": "/dir",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert "parent_directory" not in res.data
