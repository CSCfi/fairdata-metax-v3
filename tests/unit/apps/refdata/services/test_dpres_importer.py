import pytest

from apps.refdata.models import FileFormatVersion
from apps.refdata.services.importers import DPRESFileFormatVersionImporter


MOCK_DPRES_FILE_FORMAT_DATA = {
    "file_formats": [
        {
            "_id": "FI_DPRES_AAC_1",
            "mimetype": "audio/aac",
            "content_type": "audio",
            "format_name_long": "Advanced Audio Coding",
            "format_name_short": "AAC",
            "typical_extensions": [
                ".m4a",
                ".mp4",
                ".aac"
            ],
            "required_metadata": "audioMD",
            "charsets": [],
            "relations": [
                {
                    "_id": "FI_DPRES_AAC_2",
                    "type": "supersedes",
                    "dps_spec_version": "1.12.0",
                    "description": "MIME type changed from audio/aac to audio/mp4"
                }
            ],
            "versions": [
                {
                    "_id": "FI_DPRES_AAC_1_UNAP",
                    "version": "(:unap)",
                    "grade": "fi-dpres-recommended-file-format",
                    "format_registry_key": "fmt/199",
                    "support_in_dps_ingest": True,
                    "active": True,
                    "added_in_dps_spec": "1.12.0",
                    "removed_in_dps_spec": "",
                    "format_sources": [
                        {
                            "pid": "ISO_14496-3",
                            "url": "",
                            "reference": "International Organization for Standardization. Information technology — Coding of audio-visual objects — Part 3: Audio. ISO/IEC 14496-3:2019"
                        }
                    ]
                }
            ]
        },
        {
            "_id": "FI_DPRES_JSON_1",
            "mimetype": "application/json",
            "content_type": "text",
            "format_name_long": "JavaScript Object Notation",
            "format_name_short": "JSON",
            "typical_extensions": [
                ".json"
            ],
            "required_metadata": "",
            "charsets": [
                "UTF-8"
            ],
            "relations": [],
            "versions": [
                {
                    "_id": "FI_DPRES_JSON_1_UNAP",
                    "version": "(:unap)",
                    "grade": "fi-dpres-recommended-file-format",
                    "format_registry_key": "fmt/817",
                    "support_in_dps_ingest": True,
                    "active": True,
                    "added_in_dps_spec": "1.14.0",
                    "removed_in_dps_spec": "",
                    "format_sources": [
                        {
                            "pid": "ISO_21778",
                            "url": "",
                            "reference": "International Organization for Standardization. Information technology — The JSON data interchange syntax. ISO/IEC 21778:2017"
                        },
                        {
                            "pid": "RFC_8259",
                            "url": "https://datatracker.ietf.org/doc/rfc8259/",
                            "reference": "The JavaScript Object Notation (JSON) Data Interchange Format. Request for Comments: 8259. Network Working Group. December 2017."
                        }
                    ]
                }
            ]
        },
        {
            "_id": "FI_DPRES_JPEG_1",
            "mimetype": "image/jpeg",
            "content_type": "still image",
            "format_name_long": "Joint Photographic Experts Group",
            "format_name_short": "JPEG",
            "typical_extensions": [
                ".jpg",
                ".jpeg",
                ".jpe",
                ".jif",
                ".jfif",
                ".jfi"
            ],
            "required_metadata": "MIX",
            "charsets": [],
            "relations": [],
            "versions": [
                {
                    "_id": "FI_DPRES_JPEG_1_1.00",
                    "version": "1.00",
                    "grade": "fi-dpres-recommended-file-format",
                    "format_registry_key": "fmt/42",
                    "support_in_dps_ingest": True,
                    "active": True,
                    "added_in_dps_spec": "1.3.0",
                    "removed_in_dps_spec": "",
                    "format_sources": [
                        {
                            "pid": "ISO_10918-1",
                            "url": "",
                            "reference": "International Organization for Standardization. Information technology — Digital compression and coding of continuous-tone still images: Requirements and guidelines. ISO/IEC 10918-1:1994"
                        }
                    ]
                }
            ]
        }
    ]
}


pytestmark = pytest.mark.django_db


@pytest.fixture
def dpres_file_format_source(requests_mock):
    """Mock DPRES file format data"""
    requests_mock.get(
        "https://dpres-mock/file_formats.json",
        json=MOCK_DPRES_FILE_FORMAT_DATA,
    )


@pytest.mark.usefixtures("dpres_file_format_source")
def test_import_dpres_file_formats():
    importer = DPRESFileFormatVersionImporter(
        model=FileFormatVersion,
        source="https://dpres-mock/file_formats.json",
        scheme="https://mock-scheme/file-format-version",
    )
    importer.load()

    values = sorted(
        FileFormatVersion.all_objects.values(
            "url",
            "pref_label__en",
            "file_format",
            "format_version",
            "allowed_encodings"
        ),
        key=lambda v: v["url"]
    )
    assert values == [
        {
            "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_json",
            "pref_label__en": "application/json",
            "file_format": "application/json",
            "format_version": "",
            "allowed_encodings": ["UTF-8"]
        },
        {
            "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/audio_aac",
            "pref_label__en": "audio/aac",
            "file_format": "audio/aac",
            "format_version": "",
            "allowed_encodings": []
        },
        {
            "url": "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/image_jpeg_1.00",
            "pref_label__en": "image/jpeg 1.00",
            "file_format": "image/jpeg",
            "format_version": "1.00",
            "allowed_encodings": []
        }
    ]
