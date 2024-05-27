import pytest
from tests.utils import assert_nested_subdict

from apps.core import factories

pytestmark = [pytest.mark.django_db, pytest.mark.file]


@pytest.fixture
def file_tree_with_datasets(file_tree_a):
    dataset_a = factories.PublishedDatasetFactory()
    file_tree_a["dataset_a"] = dataset_a
    factories.FileSetFactory(
        dataset=dataset_a,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/sub1/file1.csv"],
            file_tree_a["files"]["/dir/sub1/file2.csv"],
            file_tree_a["files"]["/dir/sub6/file.csv"],
            file_tree_a["files"]["/dir/c.txt"],
            file_tree_a["files"]["/dir/d.txt"],
        ],
    )

    dataset_b = factories.DatasetFactory()
    file_tree_a["dataset_b"] = dataset_b
    factories.FileSetFactory(
        dataset=dataset_b,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/sub4/file.csv"],
            file_tree_a["files"]["/dir/sub6/file.csv"],
        ],
    )

    dataset_c = factories.DatasetFactory()
    file_tree_a["dataset_c"] = dataset_c
    return file_tree_a


def test_directory_dataset_a(admin_client, file_tree_with_datasets):
    res = admin_client.get(
        "/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_a"].id,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {
                "name": "dir",
                "file_count": 5,
                "size": 5 * 1024,
            },
            "directories": [
                {"name": "sub1", "file_count": 2, "size": 2 * 1024},
                {"name": "sub6", "file_count": 1, "size": 1024},
            ],
            "files": [
                {"filename": "c.txt"},
                {"filename": "d.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


def test_directory_dataset_b(admin_client, file_tree_with_datasets):
    res = admin_client.get(
        "/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_b"].id,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {
                "name": "dir",
                "file_count": 2,
                "size": 2 * 1024,
            },
            "directories": [
                {"name": "sub4", "file_count": 1, "size": 1024},
                {"name": "sub6", "file_count": 1, "size": 1024},
            ],
            "files": [],
        },
        res.data,
        check_list_length=True,
    )


def test_directory_dataset_include_all(admin_client, file_tree_with_datasets):
    res = admin_client.get(
        "/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_a"].id,
            "pagination": False,
            "include_nulls": True,
            "path": "/dir",
            "include_all": True,  # include also non-dataset files
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200

    # Response should include also non_dataset files and have the dataset_metadata field
    dm = {"dataset_metadata": None}
    assert_nested_subdict(
        {
            "directory": {
                "name": "dir",
                "file_count": 15,
                "size": 15 * 1024,
                **dm,
            },
            "directories": [
                {"name": "sub1", "file_count": 3, "size": 3 * 1024, **dm},
                {"name": "sub2", "file_count": 1, "size": 1024, **dm},
                {"name": "sub3", "file_count": 1, "size": 1024, **dm},
                {"name": "sub4", "file_count": 1, "size": 1024, **dm},
                {"name": "sub5", "file_count": 2, "size": 2 * 1024, **dm},
                {"name": "sub6", "file_count": 1, "size": 1024, **dm},
            ],
            "files": [
                {"filename": "a.txt", **dm},
                {"filename": "b.txt", **dm},
                {"filename": "c.txt", **dm},
                {"filename": "d.txt", **dm},
                {"filename": "e.txt", **dm},
                {"filename": "f.txt", **dm},
            ],
        },
        res.data,
        check_list_length=True,
    )


def test_directory_dataset_no_files_dataset(admin_client, file_tree_with_datasets):
    dataset = factories.DatasetFactory()
    res = admin_client.get(
        "/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_c"].id,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.json() == {"directories": [], "files": []}


def test_directory_exclude_dataset_a(admin_client, file_tree_with_datasets):
    res = admin_client.get(
        "/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_a"].id,
            "exclude_dataset": True,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {
                "name": "dir",
                "file_count": 10,
                "size": 10 * 1024,
            },
            "directories": [
                {
                    "name": "sub1",
                    "file_count": 1,
                    "size": 1 * 1024,
                },  # 1 file not yet in dataset
                {"name": "sub2", "file_count": 1, "size": 1 * 1024},
                {"name": "sub3", "file_count": 1, "size": 1 * 1024},
                {"name": "sub4", "file_count": 1, "size": 1 * 1024},
                {"name": "sub5", "file_count": 2, "size": 2 * 1024},
            ],
            "files": [
                {"filename": "a.txt"},
                {"filename": "b.txt"},
                {"filename": "e.txt"},
                {"filename": "f.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


def test_directory_count_published(admin_client, file_tree_with_datasets):
    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "count_published": True,  # files in dataset_a are published
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert res.data["directory"]["published_file_count"] == 5
    assert {d["pathname"]: d["published_file_count"] for d in res.data["directories"]} == {
        "/dir/sub1/": 2,
        "/dir/sub2/": 0,
        "/dir/sub3/": 0,
        "/dir/sub4/": 0,
        "/dir/sub5/": 0,
        "/dir/sub6/": 1,
    }


def test_directory_count_and_filter_published(admin_client, file_tree_a, file_tree_with_datasets):
    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "published": True,
            "count_published": True,  # files in dataset_a are published
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert res.data["directory"]["file_count"] == 15
    assert {
        d["pathname"]: (d["published_file_count"], d["file_count"])
        for d in res.data["directories"]
    } == {
        "/dir/sub1/": (2, 3),
        "/dir/sub6/": (1, 1),
    }
    assert [f["pathname"] for f in res.data["files"]] == [
        "/dir/c.txt",
        "/dir/d.txt",
    ]


def test_directory_count_and_filter_unpublished(
    admin_client, file_tree_a, file_tree_with_datasets
):
    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "published": False,
            "count_published": True,  # files in dataset_a are published
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert res.data["directory"]["file_count"] == 15
    assert {
        d["pathname"]: (d["published_file_count"], d["file_count"])
        for d in res.data["directories"]
    } == {
        "/dir/sub1/": (2, 3),
        "/dir/sub2/": (0, 1),
        "/dir/sub3/": (0, 1),
        "/dir/sub4/": (0, 1),
        "/dir/sub5/": (0, 2),
    }
    assert [f["pathname"] for f in res.data["files"]] == [
        "/dir/a.txt",
        "/dir/b.txt",
        "/dir/e.txt",
        "/dir/f.txt",
    ]

    file_tree_with_datasets["dataset_a"].file_set.files.add(
        file_tree_a["files"]["/dir/sub5/file1.csv"], file_tree_a["files"]["/dir/sub5/file2.csv"]
    )
    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "published": False,
            "count_published": True,  # files in dataset_a are published
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert {
        d["pathname"]: (d["published_file_count"], d["file_count"])
        for d in res.data["directories"]
    } == {
        "/dir/sub1/": (2, 3),
        "/dir/sub2/": (0, 1),
        "/dir/sub3/": (0, 1),
        "/dir/sub4/": (0, 1),
    }
