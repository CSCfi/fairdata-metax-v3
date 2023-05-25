import json
import os

import pytest


@pytest.fixture
def ida_file_json():
    """Example file payload from Metax V2 documentation with following changes:
    * added file_storage_pathname
    * removed not yet implemented fields: open_access
    * removed: file_name, file_format,
    * removed creation metadata: user_created, service_created
    * renamings:
       * file_storage -> storage_service (also, "urn:nbn:...:ida" changed to "ida")
       * file_uploaded -> date_uploaded
       * file_frozen -> date_frozen
       * identifier -> file_storage_identifier
    """
    return {
        "file_path": "/some/file/path/file.pdf",
        "date_uploaded": "2017-09-27T12:38:18.700Z",
        "file_modified": "2017-09-27T12:38:18.700Z",
        "date_frozen": "2017-09-27T12:38:18.700Z",
        "byte_size": 1024,
        "storage_service": "ida",
        "project_identifier": "string",
        "checksum": {
            "value": "string",
            "algorithm": "MD5",
            "checked": "2017-09-27T12:38:18.701Z",
        },
        "file_storage_identifier": "identifier",
        "file_storage_pathname": "/some/path/on/storage_service",
    }
