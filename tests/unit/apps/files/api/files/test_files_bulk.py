import uuid
from typing import List

import pytest
from rest_framework.reverse import reverse
from rest_framework.serializers import DateTimeField, RegexField
from apps.files.models import FileCharacteristics
from tests.utils import assert_nested_subdict

from apps.files import factories
from apps.files.models import File, FileStorage
from apps.files.serializers import FileSerializer

pytestmark = [pytest.mark.django_db, pytest.mark.file]


def build_files_json(file_kwargs: List[dict], storage=None):
    if storage is None:
        storage = factories.FileStorageFactory(
            csc_project="project_x",
            storage_service="ida",
        )

    factory = factories.FileFactory
    instances = []
    for kwargs in file_kwargs:
        factory_args = {k: v for k, v in kwargs.items() if k not in ["exists", "fields"]}
        if characteristics_data := factory_args.pop("characteristics", None):
            factory_args["characteristics"] = FileCharacteristics.objects.create(
                **characteristics_data
            )

        if kwargs.get("exists"):
            instances.append(factory.create(storage=storage, **factory_args))
        else:
            instances.append(factory.build(storage=storage, **factory_args))

    files = [FileSerializer(f).data for f in instances]
    for f in files:
        f.pop("record_modified", None)  # Ignored by metax
        if f.get("id") is None:
            # Remove read-only fields from new files
            f.pop("id", None)
            f.pop("record_created", None)
        if fields := kwargs.get("fields"):
            # Remove fields not specified in fields list
            for field in list(f):
                if field not in fields:
                    f.pop(field, None)
    return files


@pytest.fixture
def csc_project() -> FileStorage:
    return factories.FileStorageFactory(
        csc_project="project_x",
        storage_service="ida",
    )


@pytest.fixture
def another_csc_project() -> FileStorage:
    return factories.FileStorageFactory(
        csc_project="project_abc",
        storage_service="ida",
    )


@pytest.fixture(scope="module")
def action_url():
    def _action_url(action: str, ignore_errors=False):
        query = "?ignore_errors=true" if ignore_errors else ""
        if action == "insert":
            return reverse("file-post-many") + query
        elif action == "update":
            return reverse("file-patch-many") + query
        elif action == "upsert":
            return reverse("file-put-many") + query
        elif action == "delete":
            return reverse("file-delete-many") + query

    return _action_url


def test_files_insert_many_ok(ida_client, action_url):
    files = build_files_json(
        [
            {"id": None, "exists": False},
            {"id": None, "exists": False},
            {"id": None, "exists": False},
        ]
    )
    res = ida_client.post(
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


def test_files_insert_many_ok_missing_storage_identifier(ida_client, action_url):
    files = build_files_json(
        [
            {"id": None, "exists": False, "storage_identifier": None},
        ]
    )
    res = ida_client.post(
        action_url("insert"),
        files,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert_nested_subdict(
        [
            {
                "errors": {"storage_identifier": RegexField("Field is required")},
            }
        ],
        res.json()["failed"],
    )


def test_files_insert_many_missing_storage_identifier(ida_client, action_url):
    files = build_files_json(
        [
            {"id": None, "exists": False, "storage_identifier": None},
        ]
    )
    res = ida_client.post(
        action_url("insert", ignore_errors=True),
        files,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert_nested_subdict(
        [
            {
                "errors": {"storage_identifier": RegexField("Field is required")},
            }
        ],
        res.json()["failed"],
    )


def test_files_insert_many_multiple_storages(
    ida_client, csc_project, another_csc_project, action_url
):
    files = build_files_json([{"id": None}], storage=csc_project)
    files += build_files_json([{"id": None}], storage=another_csc_project)
    res = ida_client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "insert"},
            {"object": files[1], "action": "insert"},
        ],
        res.json()["success"],
    )


def test_files_insert_many_missing_required_fields(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": False, "fields": ["csc_project", "storage"]},
        ]
    )
    res = ida_client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 400
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {
                        "pathname": "This field is required.",
                        "modified": "This field is required.",
                        "checksum": "This field is required.",
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_insert_many_id_not_allowed(ida_client, action_url):
    files = build_files_json([{"exists": False}])
    res = ida_client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 400
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


def test_files_insert_many_file_path_already_exists(ida_client, csc_project, action_url):
    existing_files = build_files_json(
        [{"exists": True, "pathname": "/data/1.txt"}], storage=csc_project
    )
    files = build_files_json(
        [{"exists": False, "id": None, "pathname": "/data/1.txt"}], storage=csc_project
    )
    res = ida_client.post(
        action_url("insert", ignore_errors=True), files, content_type="application/json"
    )
    assert res.status_code == 400
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": {"pathname": files[0]["pathname"]},
                    "errors": {
                        "pathname": RegexField(f"already exists.*{existing_files[0]['id']}")
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_insert_many_duplicate_file_path(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": False, "id": None, "pathname": "/data/1.txt"},
            {"exists": False, "id": None, "pathname": "/data/1.txt"},
        ],
    )
    res = ida_client.post(
        action_url("insert", ignore_errors=True), files, content_type="application/json"
    )
    assert res.status_code == 207
    assert_nested_subdict(
        {
            "success": [{"object": files[0]}],
            "failed": [
                {
                    "object": files[1],
                    "errors": {"pathname": RegexField("Duplicate value")},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_insert_many_invalid_file_storage(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": False, "id": None, "pathname": "/data/1.txt"},
            {"exists": False, "id": None, "pathname": "/data/1.txt"},
        ],
    )
    files[0]["storage_service"] = "doesnotexist"
    res = ida_client.post(action_url("insert"), files, content_type="application/json")
    assert res.status_code == 400
    assert_nested_subdict(
        [{"errors": {"storage_service": RegexField("not a valid choice")}}],
        res.json()["failed"],
        check_list_length=True,
    )


def test_files_insert_many_with_external_id(ida_client, action_url):
    files = build_files_json(
        [
            {"id": None, "storage_identifier": "x"},
            {"id": None, "storage_identifier": "y"},
        ]
    )
    res = ida_client.post(
        action_url("insert"),
        files,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "insert"},
            {"object": files[1], "action": "insert"},
        ],
        res.json()["success"],
    )


def test_files_insert_many_same_external_id_different_storage(ida_client, action_url):
    storage_ida = factories.FileStorageFactory(
        csc_project="project_x",
        storage_service="ida",
    )
    storage_pas = factories.FileStorageFactory(
        csc_project="project_x",
        storage_service="pas",
    )
    files = [
        *build_files_json([{"id": None, "storage_identifier": "x"}], storage=storage_ida),
        *build_files_json([{"id": None, "storage_identifier": "x"}], storage=storage_pas),
    ]
    res = ida_client.post(
        action_url("insert"),
        files,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "insert"},
            {"object": files[1], "action": "insert"},
        ],
        res.json()["success"],
    )


def test_files_update_many_ok(ida_client, action_url):
    files = build_files_json(
        [
            {"size": 100, "exists": True},
            {"size": 200, "exists": True},
            {"size": 300, "exists": True},
        ]
    )
    res = ida_client.post(action_url("update"), files, content_type="application/json")
    assert_nested_subdict(
        [
            {"object": files[0], "action": "update"},
            {"object": files[1], "action": "update"},
            {"object": files[2], "action": "update"},
        ],
        res.json()["success"],
    )


def test_files_update_many_id_required(ida_client, action_url):
    files = build_files_json([{"exists": False, "id": None}])
    res = ida_client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 400
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {"id": "File not found."},
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_update_many_existing_file_required(ida_client, action_url):
    files = build_files_json([{"exists": True}])
    files[0]["id"] = str(uuid.uuid4())
    res = ida_client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 400
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


def test_files_update_many_read_only_field(ida_client, action_url):
    files = build_files_json([{"exists": True}])
    files[0].update(pathname="/a_new_path/file.x")
    res = ida_client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 400
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {
                        "pathname": RegexField(
                            "Cannot change value",
                        ),
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_update_many_change_project_for_existing(ida_client, action_url):
    files = build_files_json([{"exists": True}])
    factories.FileStorageFactory(
        csc_project="another_project",
        storage_service="ida",
    )
    files[0].update(csc_project="another_project")
    res = ida_client.post(action_url("update"), files, content_type="application/json")
    assert res.status_code == 400
    match_readonly = RegexField("Cannot change value")
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {
                    "object": files[0],
                    "errors": {
                        "csc_project": match_readonly,
                    },
                }
            ],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_upsert_many_ok(ida_client, action_url):
    files = build_files_json(
        [
            {"size": 100, "exists": True},
            {"size": 200, "exists": False, "id": None},
            {"size": 300, "exists": False, "id": None},
            {"size": 400, "exists": True},
        ]
    )
    res = ida_client.post(action_url("upsert"), files, content_type="application/json")
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


def test_files_upsert_many_with_external_identifier(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": True, "storage_identifier": "file1"},
            {
                "exists": False,
                "storage_identifier": "file2",
                "id": None,
            },
        ]
    )
    res = ida_client.post(action_url("upsert"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": files[0], "action": "update"},
            {"object": files[1], "action": "insert"},
        ],
        res.json()["success"],
        check_list_length=True,
    )


def test_files_upsert_many_with_missing_fields_for_new(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": True, "storage_identifier": "file1"},
            {
                "exists": False,
                "storage_identifier": "file2",
                "id": None,
            },
        ]
    )
    del files[1]["pathname"]
    del files[1]["checksum"]
    res = ida_client.post(
        action_url("upsert", ignore_errors=True), files, content_type="application/json"
    )
    assert res.status_code == 207
    assert_nested_subdict(
        {
            "success": [
                {"object": files[0], "action": "update"},
            ],
            "failed": [{"object": files[1]}],
        },
        res.json(),
        check_list_length=True,
    )


def test_files_upsert_many_unknown_field(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": True, "storage_identifier": "file1"},
        ]
    )
    files[0]["thisfielddoesnotexist"] = "something"
    res = ida_client.post(action_url("upsert"), files, content_type="application/json")
    assert res.status_code == 400
    assert_nested_subdict(
        {
            "success": [],
            "failed": [
                {"errors": {"thisfielddoesnotexist": "Unknown field"}, "object": files[0]},
            ],
        },
        res.json(),
        check_list_length=True,
    )


def set_removed(file):
    """Change file json "removed" timestamp to match any date value."""
    return {**file, "removed": DateTimeField()}


def test_files_delete_many_ok(ida_client):
    files = build_files_json(
        [
            {"exists": True},
            {"exists": True},
            {"exists": True},
        ]
    )
    res = ida_client.post("/v3/files/delete-many", files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": set_removed(files[0]), "action": "delete"},
            {"object": set_removed(files[1]), "action": "delete"},
            {"object": set_removed(files[2]), "action": "delete"},
        ],
        res.json()["success"],
    )
    assert (
        File.all_objects.filter(id__in=[f["id"] for f in files], removed__isnull=False).count()
        == 3
    )


def test_files_delete_many_only_id(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": True},
        ]
    )
    res = ida_client.post(
        action_url("delete"), [{"id": files[0]["id"]}], content_type="application/json"
    )
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": set_removed(files[0]), "action": "delete"},
        ],
        res.json()["success"],
    )
    assert (
        File.all_objects.filter(id__in=[f["id"] for f in files], removed__isnull=False).count()
        == 1
    )


def test_files_delete_many_with_external_id(ida_client, action_url):
    files = build_files_json(
        [
            {"exists": True, "storage_identifier": "file1"},
        ]
    )
    file = {
        "storage_identifier": files[0]["storage_identifier"],
        "storage_service": files[0]["storage_service"],
    }
    res = ida_client.post(action_url("delete"), [file], content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": set_removed(files[0]), "action": "delete"},
        ],
        res.json()["success"],
    )
    assert (
        File.all_objects.filter(id__in=[f["id"] for f in files], removed__isnull=False).count()
        == 1
    )


def test_files_delete_many_non_existing(ida_client):
    files = build_files_json(
        [
            {"exists": True},
            {"exists": False},
            {"exists": False},
        ]
    )
    res = ida_client.post(
        "/v3/files/delete-many?ignore_errors=true", files, content_type="application/json"
    )
    assert res.status_code == 207
    assert_nested_subdict(
        {
            "success": [
                {"object": set_removed(files[0]), "action": "delete"},
            ],
            "failed": [
                {"object": files[1], "errors": {"id": "File with id not found."}},
                {"object": files[2], "errors": {"id": "File with id not found."}},
            ],
        },
        res.json(),
    )
    File.all_objects.filter(id__in=[f["id"] for f in files], removed__isnull=False).count() == 3


def test_files_delete_many_multiple_projects(
    ida_client, csc_project, another_csc_project, action_url
):
    files = build_files_json([{"exists": True}], storage=csc_project)
    files += build_files_json([{"exists": True}], storage=another_csc_project)
    res = ida_client.post(action_url("delete"), files, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": set_removed(files[0]), "action": "delete"},
            {"object": set_removed(files[1]), "action": "delete"},
        ],
        res.json()["success"],
    )


def test_files_delete_duplicate_id(ida_client, csc_project, another_csc_project, action_url):
    files = build_files_json([{"exists": True}], storage=csc_project)
    files += files
    res = ida_client.post(
        action_url("delete", ignore_errors=True), files, content_type="application/json"
    )
    assert res.status_code == 207
    assert_nested_subdict(
        {
            "success": [
                {"object": set_removed(files[0]), "action": "delete"},
            ],
            "failed": [
                {"object": files[1], "errors": {"id": RegexField("Duplicate file")}},
            ],
        },
        res.json(),
    )


def test_files_bulk_delete_unknown_storage_identifier(ida_client, csc_project, action_url):
    res = ida_client.post(
        action_url("delete", ignore_errors=True),
        [{"storage_service": "ida", "storage_identifier": "jeejee"}],
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json()["failed"][0] == {
        "object": {"storage_identifier": "jeejee", "storage_service": "ida"},
        "errors": {"id": "File not found."},
    }


def test_files_bulk_delete_missing_storage_service(ida_client, csc_project, action_url):
    res = ida_client.post(
        action_url("delete", ignore_errors=True),
        [{"storage_identifier": "jeejee"}],
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json()["failed"][0] == {
        "object": {"storage_identifier": "jeejee"},
        "errors": {
            "id": "File not found.",
            "storage_service": "Either storage_service or id is required.",
        },
    }


def test_files_bulk_delete_missing_storage_identifier(ida_client, csc_project, action_url):
    res = ida_client.post(
        action_url("delete", ignore_errors=True),
        [{"storage_service": "ida"}],
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json()["failed"][0] == {
        "object": {"storage_service": "ida"},
        "errors": {
            "id": "File not found.",
            "storage_identifier": "Either storage_identifier or id is required.",
        },
    }
