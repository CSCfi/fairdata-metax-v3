import pytest
from django.contrib.admin.sites import AdminSite

from apps.files.admin import FileStorageProxyAdmin
from apps.files.factories import FileStorageFactory
from apps.files.models.file_storage import FileStorage

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


def test_file_storage_admin():
    admin = FileStorageProxyAdmin(model=FileStorage, admin_site=AdminSite())
    storage = FileStorageFactory(storage_service="ida", csc_project="1234")
    path = "/v3/directories?storage_service=ida&csc_project=1234"
    assert admin.project_root(storage) == f'<a href="{path}">{path}</a>'
