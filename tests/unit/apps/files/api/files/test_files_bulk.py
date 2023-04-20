import uuid
from typing import List

import pytest
from rest_framework.reverse import reverse
from rest_framework.serializers import RegexField
from tests.utils import assert_nested_subdict

from apps.files import factories
from apps.files.models import File, StorageProject
from apps.files.serializers import FileSerializer


def build_files_json(file_kwargs: List[dict], project=None):
    if project is None:
        project = factories.StorageProjectFactory(
            project_identifier="project_x",
            file_storage__id="ida",
        )

    factory = factories.FileFactory
    instances = []
    for kwargs in file_kwargs:
        factory_args = {k: v for k, v in kwargs.items() if k not in ["exists", "fields"]}
        if kwargs.get("exists"):
            instances.append(factory.create(storage_project=project, **factory_args))
        else:
            instances.append(factory.build(storage_project=project, **factory_args))

    files = [FileSerializer(f).data for f in instances]
    for f in files:
        f.pop("modified", None)  # Ignored by metax
        if f.get("id") is None:
            # Remove read-only fields from new files
            f.pop("id", None)
            f.pop("created", None)
        if fields := kwargs.get("fields"):
            # Remove fields not specified in fields list
            for field in list(f):
                if field not in fields:
                    f.pop(field, None)
    return files


@pytest.fixture
def project() -> StorageProject:
    return factories.StorageProjectFactory(
        project_identifier="project_x",
        file_storage__id="ida",
    )


@pytest.fixture
def another_project() -> StorageProject:
    return factories.StorageProjectFactory(
        project_identifier="project_abc",
        file_storage__id="ida",
    )


@pytest.fixture
def another_storage() -> StorageProject:
    return factories.StorageProjectFactory(
        project_identifier="project_x",
        file_storage__id="xyz-storage",
    )

@pytest.fixture(scope="module")
def action_url():
    def _action_url(action: str):
        if action == "insert":
            return reverse('file-insert-many')
        elif action == "update":
            return reverse('file-update-many')
        elif action == 'upsert':
            return reverse('file-upsert-many')
        elif action == "delete":
            return reverse('file-delete-many')
    return _action_url

@pytest.mark.django_db
def test_files_insert_many_ok(client, action_url):
    files = build_files_json(
        [
            {"id": None, "exists": False},
            {"id": None, "exists": False},
            {"id": None, "exists": False},
        ]
    )
    res = client.post(
        action_url("insert"),
        files,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "insert"},
            {"object": files[1], "action": "insert"},
            {"object": files[2], "action": "insert"},
        ],
        res.json()["success"],
    )


@pytest.mark.django_db
def test_files_insert_many_multiple_projects(client, project, another_project, action_url):
    files = build_files_json([{"id": None}], project=project)
    files += build_files_json([{"id": None}], project=another_project)
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "insert"},
            {"object": files[1], "action": "insert"},
        ],
        res.json()["success"],
    )


@pytest.mark.django_db
def test_files_insert_many_multiple_storages(client, project, another_storage, action_url):
    files = build_files_json([{"id": None}], project=project)
    files += build_files_json([{"id": None}], project=another_storage)
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "insert"},
            {"object": files[1], "action": "insert"},
        ],
        res.json()["success"],
    )


@pytest.mark.django_db
def test_files_insert_many_missing_required_fields(client, action_url):
    files = build_files_json(
        [
            {"exists": False, "fields": ["project_identifier", "file_storage"]},
        ]
    )
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {
                        "date_uploaded": "Field is required for new files.",
                        "file_path": "Field is required for new files.",
                        "file_modified": "Field is required for new files.",
                        "checksum": "Field is required for new files.",
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_insert_many_id_not_allowed(client, action_url):
    files = build_files_json([{"exists": False}])
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": {"id": files[0]["id"]},
                    "errors": {"id": RegexField("not allowed for inserting")},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {"id": RegexField("not allowed")},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_insert_many_file_path_already_exists(client, project, action_url):
    existing_files = build_files_json(
        [{"exists": True, "file_path": "/data/1.txt"}], project=project
    )
    files = build_files_json(
        [{"exists": False, "id": None, "file_path": "/data/1.txt"}], project=project
    )
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": {"file_path": files[0]["file_path"]},
                    "errors": {
                        "file_path": RegexField(f"already exists.*{existing_files[0]['id']}")
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_insert_many_duplicate_file_path(client, action_url):
    files = build_files_json(
        [
            {"exists": False, "id": None, "file_path": "/data/1.txt"},
            {"exists": False, "id": None, "file_path": "/data/1.txt"},
        ],
    )
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [{"object": files[0]}],
            "failed": [
                {
                    "object": files[1],
                    "errors": {"file_path": RegexField("conflicts")},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_insert_many_invalid_file_storage(client, action_url):
    files = build_files_json(
        [
            {"exists": False, "id": None, "file_path": "/data/1.txt"},
            {"exists": False, "id": None, "file_path": "/data/1.txt"},
        ],
    )
    files[0]["file_storage"] = "doesnotexist"
    files[1]["file_storage"] = "doesnotexist"
    res = client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {"file_storage": RegexField("not found")},
                },
                {
                    "object": files[1],
                    "errors": {"file_storage": RegexField("not found")},
                },
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_update_many_ok(client, action_url):
    files = build_files_json(
        [
            {"byte_size": 100, "exists": True},
            {"byte_size": 200, "exists": True},
            {"byte_size": 300, "exists": True},
        ]
    )
    res = client.post(action_url("update"), files, content_type="application/json")
    assert_nested_subdict(
        [
            {"object": files[0], "action": "update"},
            {"object": files[1], "action": "update"},
            {"object": files[2], "action": "update"},
        ],
        res.json()["success"],
    )


@pytest.mark.django_db
def test_files_update_many_id_required(client, action_url):
    files = build_files_json([{"exists": False, "id": None}])
    res = client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {"id": "Expected an existing file."},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_update_many_existing_file_required(client, action_url):
    files = build_files_json([{"exists": True}])
    files[0]["id"] = str(uuid.uuid4())
    res = client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {"id": RegexField("id not found")},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_update_many_read_only_field(client, action_url):
    files = build_files_json([{"exists": True}])
    files[0].update(file_path="/a_new_path/file.x")
    res = client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {
                        "file_path": RegexField(
                            "Cannot change value",
                        ),
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_update_many_change_project_for_existing(client, action_url):
    files = build_files_json([{"exists": True}])
    files[0].update(project_identifier="/a_new_path/file.x", file_storage="something_else")
    res = client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 200
    match_readonly = RegexField("Cannot change value")
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {
                        "project_identifier": match_readonly,
                        "file_storage": match_readonly,
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


@pytest.mark.django_db
def test_files_upsert_many_ok(client, action_url):
    files = build_files_json(
        [
            {"byte_size": 100, "exists": True},
            {"byte_size": 200, "exists": False, "id": None},
            {"byte_size": 300, "exists": False, "id": None},
            {"byte_size": 400, "exists": True},
        ]
    )
    res = client.post(action_url("upsert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "update"},
            {"object": files[1], "action": "insert"},
            {"object": files[2], "action": "insert"},
            {"object": files[3], "action": "update"},
        ],
        res.json()["success"],
    )


@pytest.mark.django_db
def test_files_delete_many_ok(client):
    files = build_files_json(
        [
            {"exists": True},
            {"exists": True},
            {"exists": True},
        ]
    )
    res = client.post("/rest/v3/files/delete-many", files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "delete"},
            {"object": files[1], "action": "delete"},
            {"object": files[2], "action": "delete"},
        ],
        res.json()["success"],
    )
    File.all_objects.filter(id__in=[f["id"] for f in files], is_removed=True).count() == 3


@pytest.mark.django_db
def test_files_delete_many_only_id(client, action_url):
    files = build_files_json(
        [
            {"exists": True},
        ]
    )
    res = client.post(
        action_url("delete"), [{"id": files[0]["id"]}], content_type="application/json"
    )
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "delete"},
        ],
        res.json()["success"],
    )
    File.all_objects.filter(id__in=[f["id"] for f in files], is_removed=True).count() == 1


@pytest.mark.django_db
def test_files_delete_many_non_existing(client):
    files = build_files_json(
        [
            {"exists": True},
            {"exists": False},
            {"exists": False},
        ]
    )
    res = client.post("/rest/v3/files/delete-many", files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [
                {"object": files[0], "action": "delete"},
            ],
            "failed": [
                {"object": files[1], "errors": {"id": "File with id not found."}},
                {"object": files[2], "errors": {"id": "File with id not found."}},
            ],
        },
        res.json(),
    )
    File.all_objects.filter(id__in=[f["id"] for f in files], is_removed=True).count() == 3


@pytest.mark.django_db
def test_files_delete_many_multiple_projects(client, project, another_project, action_url):
    files = build_files_json([{"exists": True}], project=project)
    files += build_files_json([{"exists": True}], project=another_project)
    res = client.post(action_url("delete"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "delete"},
            {"object": files[1], "action": "delete"},
        ],
        res.json()["success"],
    )


@pytest.mark.django_db
def test_files_delete_duplicate_id(client, project, another_project, action_url):
    files = build_files_json([{"exists": True}], project=project)
    files += files
    res = client.post(action_url("delete"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "success": [
                {"object": files[0], "action": "delete"},
            ],
            "failed": [
                {"object": files[1], "errors": {"id": RegexField("Duplicate file")}},
            ],
        },
        res.json(),
    )
