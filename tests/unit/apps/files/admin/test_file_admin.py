import pytest
from rest_framework.reverse import reverse

from apps.files.factories import FileStorageFactory, FileFactory

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


def test_file_admin_changelist_storage(admin_client):
    storage1 = FileStorageFactory(storage_service="ida", csc_project="proj1")
    FileFactory(storage=storage1)
    FileFactory(storage=storage1)
    FileFactory(storage=storage1)

    storage2 = FileStorageFactory(storage_service="ida", csc_project="proj2")
    FileFactory(storage=storage2)
    FileFactory(storage=storage2)

    storage3 = FileStorageFactory(storage_service="pas", csc_project="proj1")
    FileFactory(storage=storage3)

    url = reverse("admin:files_file_changelist")
    res = admin_client.get(url)  # Return none by default
    assert len(res.context["cl"].result_list) == 0

    res = admin_client.get(url, {"storage": "ida:*"})
    assert len(res.context["cl"].result_list) == 5

    res = admin_client.get(url, {"storage": "ida:proj1"})
    assert len(res.context["cl"].result_list) == 3

    res = admin_client.get(url, {"storage": "ida:proj2"})
    assert len(res.context["cl"].result_list) == 2

    res = admin_client.get(url, {"storage": "pas:*"})
    assert len(res.context["cl"].result_list) == 1

    res = admin_client.get(url, {"storage": "pas:proj1"})
    assert len(res.context["cl"].result_list) == 1


def test_file_admin_changelist_search_storage_identifier(admin_client):
    storage = FileStorageFactory(storage_service="ida", csc_project="proj")
    FileFactory(storage_identifier="storageidentifier1", storage=storage)
    FileFactory(storage_identifier="storageidentifier2", storage=storage)
    FileFactory(storage_identifier="storageidentifier3", storage=storage)

    url = reverse("admin:files_file_changelist")
    res = admin_client.get(url, {"storage": "ida:*", "q": "storageidentifier"})
    assert len(res.context["cl"].result_list) == 3

    res = admin_client.get(url, {"storage": "ida:*", "q": "storageidentifier1"})
    assert len(res.context["cl"].result_list) == 1


def test_file_admin_changelist_search_id(admin_client):
    storage = FileStorageFactory(storage_service="ida", csc_project="proj")
    f1 = FileFactory(storage_identifier="storageidentifier1", storage=storage)
    f2 = FileFactory(storage_identifier="storageidentifier2", storage=storage)

    url = reverse("admin:files_file_changelist")
    res = admin_client.get(url, {"storage": "ida:*", "q": str(f1.id)})
    assert len(res.context["cl"].result_list) == 1
    assert res.context["cl"].result_list[0].id == f1.id

    res = admin_client.get(url, {"storage": "ida:*", "q": str(f2.id)})
    assert len(res.context["cl"].result_list) == 1
    assert res.context["cl"].result_list[0].id == f2.id


@pytest.fixture
def files_with_paths():
    storage = FileStorageFactory(storage_service="ida", csc_project="proj")
    FileFactory(pathname="/dir1/file1.txt", storage=storage)
    FileFactory(pathname="/dir1/file2.txt", storage=storage)
    FileFactory(pathname="/dir1/fine_subdir/file3.txt", storage=storage)
    FileFactory(pathname="/dir2/file4.txt", storage=storage)


def test_file_admin_changelist_search_pathname(admin_client, files_with_paths):
    # Pathname ends with '/' --> search only directory_path
    url = reverse("admin:files_file_changelist")
    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir1/"})
    assert len(res.context["cl"].result_list) == 3

    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir1/fine_subdir/"})
    assert len(res.context["cl"].result_list) == 1

    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir2/"})
    assert len(res.context["cl"].result_list) == 1

    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir2/file4.txt/"})
    assert len(res.context["cl"].result_list) == 0

    # Pathname does not end with '/' --> search also filenames
    url = reverse("admin:files_file_changelist")
    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir"})
    assert len(res.context["cl"].result_list) == 4

    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir1/fi"})
    assert len(res.context["cl"].result_list) == 3

    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir1/file"})
    assert len(res.context["cl"].result_list) == 2

    res = admin_client.get(url, {"storage": "ida:*", "q": "/dir1/file1.txt"})
    assert len(res.context["cl"].result_list) == 1


def test_file_admin_changes(admin_client):
    f = FileFactory(pathname="/dir1/file1.txt")

    url = reverse("admin:files_file_change", [str(f.id)])
    res = admin_client.get(url)
    assert res.status_code == 200

    f.delete()  # Soft deleted file should be viewable with direct url
    url = reverse("admin:files_file_change", [str(f.id)])
    res = admin_client.get(url)
    assert res.status_code == 200

    f.delete(soft=False)
    url = reverse("admin:files_file_change", [str(f.id)])
    res = admin_client.get(url)
    assert res.status_code == 302  # not found, redirects another admin view
