import pytest
from tests.utils import assert_nested_subdict


@pytest.mark.django_db
def test_directory_path(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "path": "/dir",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {"file_count": 15, "byte_size": 15 * 1024},
            "directories": [
                {"directory_name": "sub1"},
                {"directory_name": "sub2"},
                {"directory_name": "sub3"},
                {"directory_name": "sub4"},
                {"directory_name": "sub5"},
                {"directory_name": "sub6"},
            ],
            "files": [
                {"file_name": "a.txt"},
                {"file_name": "b.txt"},
                {"file_name": "c.txt"},
                {"file_name": "d.txt"},
                {"file_name": "e.txt"},
                {"file_name": "f.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_path_subdir(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "path": "/dir/sub1",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {"file_count": 3, "byte_size": 3 * 1024},
            "directories": [],
            "files": [
                {"file_name": "file1.csv"},
                {"file_name": "file2.csv"},
                {"file_name": "file3.csv"},
            ],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_path_nonexisting(client, file_tree_a):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "path": "/thispathdoesnotexist",
            **file_tree_a["params"],
        },
    )
    assert res.status_code == 200
    assert res.data == {"directories": [], "files": []}
