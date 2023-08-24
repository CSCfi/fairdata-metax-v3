import pytest
from tests.utils import assert_nested_subdict


@pytest.mark.django_db
def test_directory_path(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "pagination": False,
            "path": "/dir",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {"file_count": 15, "size": 15 * 1024},
            "directories": [
                {"name": "sub1"},
                {"name": "sub2"},
                {"name": "sub3"},
                {"name": "sub4"},
                {"name": "sub5"},
                {"name": "sub6"},
            ],
            "files": [
                {"filename": "a.txt"},
                {"filename": "b.txt"},
                {"filename": "c.txt"},
                {"filename": "d.txt"},
                {"filename": "e.txt"},
                {"filename": "f.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_path_subdir(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "pagination": False,
            "path": "/dir/sub1",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {"file_count": 3, "size": 3 * 1024},
            "directories": [],
            "files": [
                {"filename": "file1.csv"},
                {"filename": "file2.csv"},
                {"filename": "file3.csv"},
            ],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_path_nonexisting(client, file_tree_a):
    res = client.get(
        "/v3/directories",
        {
            "pagination": False,
            "path": "/thispathdoesnotexist",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert res.data == {"directories": [], "files": []}
