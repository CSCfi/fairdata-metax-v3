import pytest
from rest_framework.reverse import reverse
from apps.files.models.file import FileCharacteristics
from tests.utils import assert_nested_subdict

from apps.core import factories
from apps.files.models import File

pytestmark = [pytest.mark.django_db, pytest.mark.file]

characteristics_detail_json = {
    "file_format_version": {
        "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/text_csv"
    },
    "encoding": "UTF-8",
    "csv_has_header": False,
    "csv_quoting_char": '"',
    "csv_delimiter": ",",
    "csv_record_separator": "LF",
}


characteristics_json = {
    "characteristics": characteristics_detail_json,
    "characteristics_extension": {"some_stuff_here": "value"},
}


def assert_csv_characteristics(characteristics: FileCharacteristics, encoding="UTF-8"):
    assert characteristics.encoding == encoding
    assert characteristics.csv_quoting_char == '"'
    assert characteristics.csv_delimiter == ","
    assert characteristics.csv_record_separator == "LF"
    assert (
        characteristics.file_format_version.url
        == "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/text_csv"
    )


def assert_pdf_characteristics(characteristics: FileCharacteristics):
    assert characteristics.encoding is None
    assert characteristics.csv_quoting_char is None
    assert characteristics.csv_delimiter is None
    assert characteristics.csv_record_separator is None
    assert (
        characteristics.file_format_version.url
        == "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2"
    )


def test_files_create_file_with_characteristics(
    ida_client, ida_file_json, file_format_reference_data
):
    """Create file with characteristics."""
    file_json = {**ida_file_json, **characteristics_json}

    res = ida_client.post(reverse("file-list"), file_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(file_json, res.json())
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}


def test_files_update_file_with_characteristics(
    ida_client, ida_file_json, file_format_reference_data
):
    """Update characteristics of existing file."""
    res = ida_client.post(reverse("file-list"), ida_file_json, content_type="application/json")
    assert res.status_code == 201

    # Add characteristics to existing file
    file_id = res.json()["id"]
    file_json = {"id": file_id, **characteristics_json}
    res = ida_client.patch(
        reverse("file-detail", kwargs={"pk": file_id}), file_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert_nested_subdict(file_json, res.json())
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}

    # Update characteristics
    file_json["characteristics"] = {
        "file_format_version": {
            "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2"
        }
    }
    res = ida_client.patch(
        reverse("file-detail", kwargs={"pk": file_id}), file_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert_nested_subdict(file_json, res.json())
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_pdf_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}

    # Remove characteristics
    file_json = {"id": file_id, "characteristics": None}
    res = ida_client.patch(
        reverse("file-detail", kwargs={"pk": file_id}), file_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert "characteristics" not in res.json()
    assert FileCharacteristics.objects.count() == 0  # Orphaned characteristics object is deleted


def test_files_insert_many_characteristics(ida_client, ida_file_json, file_format_reference_data):
    """Create file with characteristics using bulk API."""
    file_json = {**ida_file_json, **characteristics_json}

    res = ida_client.post(reverse("file-post-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": file_json, "action": "insert"},
        ],
        res.json()["success"],
    )
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}


def test_files_update_many_characteristics(ida_client, ida_file_json, file_format_reference_data):
    """Update characteristics of existing file using bulk API."""
    res = ida_client.post(
        reverse("file-post-many"), [ida_file_json], content_type="application/json"
    )

    # Add characteristics to existing file
    file_id = res.json()["success"][0]["object"]["id"]
    file_json = {"id": file_id, **characteristics_json}
    res = ida_client.post(reverse("file-patch-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": file_json, "action": "update"},
        ],
        res.json()["success"],
    )
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}

    # Update characteristics
    file_json["characteristics"] = {
        "file_format_version": {
            "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2"
        }
    }
    res = ida_client.post(reverse("file-patch-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": file_json, "action": "update"},
        ],
        res.json()["success"],
    )
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_pdf_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}

    # Remove characteristics
    file_json = {"id": file_id, "characteristics": None}
    res = ida_client.post(reverse("file-patch-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert "characteristics" not in res.json()["success"][0]["object"]
    assert FileCharacteristics.objects.count() == 0  # Orphaned characteristics object is deleted


def test_files_update_many_characteristics(ida_client, ida_file_json, file_format_reference_data):
    """Update characteristics of existing file using bulk API."""
    res = ida_client.post(
        reverse("file-post-many"), [ida_file_json], content_type="application/json"
    )

    # Add characteristics to existing file
    file_id = res.json()["success"][0]["object"]["id"]
    file_json = {"id": file_id, **characteristics_json}
    res = ida_client.post(reverse("file-patch-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": file_json, "action": "update"},
        ],
        res.json()["success"],
    )
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}

    # Update characteristics
    file_json["characteristics"] = {
        "file_format_version": {
            "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2"
        }
    }
    res = ida_client.post(reverse("file-patch-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"object": file_json, "action": "update"},
        ],
        res.json()["success"],
    )
    assert FileCharacteristics.objects.count() == 1
    file = File.objects.first()
    assert_pdf_characteristics(file.characteristics)
    assert file.characteristics_extension == {"some_stuff_here": "value"}

    # Remove characteristics
    file_json = {"id": file_id, "characteristics": None}
    res = ida_client.post(reverse("file-patch-many"), [file_json], content_type="application/json")
    assert res.status_code == 200
    assert "characteristics" not in res.json()["success"][0]["object"]
    assert FileCharacteristics.objects.count() == 0  # Orphaned characteristics object is deleted


def test_files_file_characteristics_create(ida_client, ida_file_json, file_format_reference_data):
    """Add characteristics to existing file using characteristic endpoint."""
    res = ida_client.post(reverse("file-list"), ida_file_json, content_type="application/json")
    assert res.status_code == 201

    # Add characteristics to existing file
    file_id = res.json()["id"]
    res = ida_client.put(
        reverse("file-characteristics-detail", kwargs={"pk": file_id}),
        characteristics_detail_json,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert_nested_subdict(characteristics_detail_json, res.json())
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics)
    assert FileCharacteristics.objects.count() == 1


def test_files_file_characteristics_patch(ida_client, ida_file_json, file_format_reference_data):
    """Update existing characteristics using characteristic endpoint."""
    file_json = {**ida_file_json, **characteristics_json}
    res = ida_client.post(reverse("file-list"), file_json, content_type="application/json")
    assert res.status_code == 201

    # Patch characteristics
    file_id = res.json()["id"]
    res = ida_client.patch(
        reverse("file-characteristics-detail", kwargs={"pk": file_id}),
        {"encoding": "UTF-16"},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict({**characteristics_detail_json, "encoding": "UTF-16"}, res.json())
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics, encoding="UTF-16")
    assert FileCharacteristics.objects.count() == 1


def test_files_file_characteristics_patch_error(
    ida_client, ida_file_json, file_format_reference_data
):
    """Patch using invalid encoding value."""
    file_json = {**ida_file_json, **characteristics_json}
    res = ida_client.post(reverse("file-list"), file_json, content_type="application/json")
    assert res.status_code == 201

    # Patch characteristics
    file_id = res.json()["id"]
    res = ida_client.patch(
        reverse("file-characteristics-detail", kwargs={"pk": file_id}),
        {"encoding": "UTF-1337"},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "not a valid choice" in res.json()["encoding"][0]
    assert FileCharacteristics.objects.count() == 1


def test_files_file_characteristics_delete(ida_client, ida_file_json, file_format_reference_data):
    """Update existing characteristics using characteristic endpoint."""
    file_json = {**ida_file_json, **characteristics_json}
    res = ida_client.post(reverse("file-list"), file_json, content_type="application/json")
    assert res.status_code == 201
    assert FileCharacteristics.objects.count() == 1

    # Remove characteristics
    file_id = res.json()["id"]
    res = ida_client.delete(reverse("file-characteristics-detail", kwargs={"pk": file_id}))
    assert res.status_code == 204
    assert FileCharacteristics.objects.count() == 0


def test_files_file_characteristics_permissions_project_member(
    user_client, ida_client, ida_file_json, file_format_reference_data
):
    """Update existing characteristics using characteristic endpoint as csc_project member."""
    file_json = {**ida_file_json, **characteristics_json}
    res = ida_client.post(reverse("file-list"), file_json, content_type="application/json")
    assert res.status_code == 201

    # Patch characteristics should fail without permission to dataset or project
    file_id = res.json()["id"]
    url = reverse("file-characteristics-detail", kwargs={"pk": file_id})
    res = user_client.patch(url, {"encoding": "UTF-16"}, content_type="application/json")
    assert res.status_code == 404

    # Add user to csc_project, patch should now work
    user = user_client._user
    user.csc_projects = [file_json["csc_project"]]
    user.save()

    res = user_client.patch(url, {"encoding": "UTF-16"}, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict({**characteristics_detail_json, "encoding": "UTF-16"}, res.json())
    file = File.objects.first()
    assert_csv_characteristics(file.characteristics, encoding="UTF-16")
    assert FileCharacteristics.objects.count() == 1


def test_files_file_characteristics_permissions_shared_dataset(
    user_client, ida_client, ida_file_json, file_format_reference_data
):
    """Update existing characteristics using characteristic endpoint as a dataset editor."""
    file_json = {**ida_file_json, **characteristics_json}
    res = ida_client.post(reverse("file-list"), file_json, content_type="application/json")
    assert res.status_code == 201

    # Patch characteristics should fail without permission to dataset or project
    file_id = res.json()["id"]
    url = reverse("file-characteristics-detail", kwargs={"pk": file_id})
    res = user_client.patch(url, {"encoding": "UTF-16"}, content_type="application/json")
    assert res.status_code == 404

    # Create dataset that contains file
    dataset = factories.DatasetFactory()
    dataset.permissions.editors.add(user_client._user)
    file = File.objects.first()
    factories.FileSetFactory(dataset=dataset, storage=file.storage, files=[file])

    # Patch should still fail unless dataset is explicitly set in the query string
    res = user_client.patch(url, {"encoding": "UTF-16"}, content_type="application/json")
    assert res.status_code == 404

    res = user_client.patch(
        f"{url}?dataset={dataset.id}", {"encoding": "UTF-16"}, content_type="application/json"
    )
    assert res.status_code == 200
    assert_nested_subdict({**characteristics_detail_json, "encoding": "UTF-16"}, res.json())
    file.refresh_from_db()
    assert_csv_characteristics(file.characteristics, encoding="UTF-16")
    assert FileCharacteristics.objects.count() == 1
