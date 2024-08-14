import pytest
from django.contrib.auth.models import Group

from apps.files.factories import create_v2_file_data
from apps.files.models import File
from apps.users.models import MetaxUser

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
    pytest.mark.adapter,
    pytest.mark.usefixtures("data_catalog", "reference_data", "v2_integration_settings"),
]


def test_files_from_legacy(admin_client):
    file_data = create_v2_file_data(
        {
            "ida:project_x": [
                "/data/file1",
                "/data/file2",
                "/data/file3",
            ],
            "pas:project_y": [
                "/readme.md",
                "/license.txt",
            ],
            "pas:project_z": ["/dir1/y1.txt", "/dir1/y2.txt", "-/dir1/y3.txt", "/dir2/z.txt"],
        },
    )

    resp = admin_client.post("/v3/files/from-legacy", file_data, content_type="application/json")
    assert resp.status_code == 200
    assert resp.data == {
        "created": 9,
        "updated": 0,
        "unchanged": 0,
    }

    # Edit files so we can test updating them using from-legacy works properly
    File.all_objects.get(filename="file1").delete(soft=False)  # hard delete
    File.objects.get(filename="readme.md").delete()  # mark as soft deleted
    assert File.all_objects.filter(directory_path="/dir1/").update(size=123) == 3
    assert File.all_objects.count() == 8
    assert list(
        File.all_objects.filter(directory_path="/dir1/").values_list("size", flat=True)
    ) == [123, 123, 123]

    # Sync files again, which should return them back to the initial state
    resp = admin_client.post("/v3/files/from-legacy", file_data, content_type="application/json")
    assert resp.status_code == 200
    assert resp.data == {
        "created": 1,
        "updated": 4,
        "unchanged": 4,
    }
    assert [
        (f.storage.storage_service, f.storage.csc_project, f.pathname, bool(f.removed))
        for f in File.all_objects.order_by("legacy_id").all()
    ] == [
        ("ida", "project_x", "/data/file1", False),
        ("ida", "project_x", "/data/file2", False),
        ("ida", "project_x", "/data/file3", False),
        ("pas", "project_y", "/readme.md", False),
        ("pas", "project_y", "/license.txt", False),
        ("pas", "project_z", "/dir1/y1.txt", False),
        ("pas", "project_z", "/dir1/y2.txt", False),
        ("pas", "project_z", "/dir1/y3.txt", True),
        ("pas", "project_z", "/dir2/z.txt", False),
    ]
    assert list(
        File.all_objects.filter(directory_path="/dir1/").values_list("size", flat=True)
    ) == [
        1000,
        1000,
        1000,
    ]


def test_files_from_legacy_permissions(service_client):
    resp = service_client.post("/v3/files/from-legacy", [], content_type="application/json")
    assert resp.status_code == 403

    # The from-legacy endpoint should only be allowed for the v2_migration group
    user = MetaxUser.objects.get(username="service_test")
    user.groups.add(Group.objects.create(name="v2_migration"))
    resp = service_client.post("/v3/files/from-legacy", [], content_type="application/json")
    assert resp.status_code == 200
