import pytest
from django.conf import settings
from requests import request

from apps.refdata.models import AccessType, FileFormatVersion, License
from apps.refdata.services.importers import (
    LocalJSONFileFormatVersionImporter,
    LocalJSONImporter,
    LocalJSONLicenseImporter,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def local_ref_data_importer():
    def _local_ref_data_importer(
        importer_class, data_source: str, model, source=None, scheme=None
    ):
        data_source = settings.LOCAL_REFERENCE_DATA_SOURCES[data_source]
        return importer_class(
            model=model,
            source=source or data_source["source"],
            scheme=scheme or data_source["scheme"],
        )

    return _local_ref_data_importer


def test_import_local_json(local_ref_data_importer):
    importer = local_ref_data_importer(LocalJSONImporter, "access_type", AccessType)
    assert AccessType.all_objects.count() == 0
    importer.load()
    open_access = AccessType.all_objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
    )
    assert open_access.in_scheme == importer.scheme
    assert open_access.pref_label == {"en": "Open", "fi": "Avoin"}


def test_import_local_json_license(local_ref_data_importer):
    importer = local_ref_data_importer(LocalJSONLicenseImporter, "license", License)
    # assert License.all_objects.count() == 1  # there's Other license by default
    importer.load()
    ccby = License.all_objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
    )
    assert ccby.in_scheme == importer.scheme
    assert ccby.pref_label == {
        "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
    }
    assert ccby.same_as == ["https://creativecommons.org/licenses/by/4.0/"]


def test_import_local_json_file_format(local_ref_data_importer):
    importer = local_ref_data_importer(
        LocalJSONFileFormatVersionImporter, "file_format_version", FileFormatVersion
    )
    assert FileFormatVersion.all_objects.count() == 0
    importer.load()
    pdf = FileFormatVersion.all_objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_A-2b"
    )
    assert pdf.in_scheme == importer.scheme
    assert pdf.pref_label == {
        "en": "application/pdf A-2b",
        "fi": "application/pdf A-2b",
        "und": "application/pdf A-2b",
    }
    assert pdf.file_format == "application/pdf"
    assert pdf.format_version == "A-2b"
