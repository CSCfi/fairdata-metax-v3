import os, json
import pytest


@pytest.fixture
def ida_file_json():
    """Example file payload from Metax V2 documentation with following changes:
    * removed not yet implemented fields: identifier, open_access
    * removed: file_name, file_format,
    * removed creation metadata: user_created, service_created
    * renamed file_uploaded -> date_uploaded, file_frozen -> date_frozen"""
    return {
        "file_path": "/some/file/path/file.pdf",
        "date_uploaded": "2017-09-27T12:38:18.700Z",
        "file_modified": "2017-09-27T12:38:18.700Z",
        "date_frozen": "2017-09-27T12:38:18.700Z",
        "byte_size": 1024,
        "file_storage": "urn:nbn:fi:att:file-storage-ida",
        "project_identifier": "string",
        "checksum": {
            "value": "string",
            "algorithm": "MD5",
            "checked": "2017-09-27T12:38:18.701Z",
        },
    }
