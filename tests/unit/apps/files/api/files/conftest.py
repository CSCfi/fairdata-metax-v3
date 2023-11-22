import json
import os

import pytest


@pytest.fixture
def ida_file_json():
    """Example file payload from Metax V2 documentation with following changes:
    * checksum object converted into string
    * removed not yet implemented fields: open_access
    * removed: filename, file_format,
    * removed creation metadata: service_created
    * removed date_uploaded
    * renamings:
       * file_path -> pathname
       * file_storage -> storage_service (also, "urn:nbn:...:ida" changed to "ida")
       * file_frozen -> frozen
       * identifier -> storage_identifier
       * byte_size -> size
       * project_identifier -> csc_project
       * user_created -> user

    """
    return {
        "pathname": "/some/file/path/file.pdf",
        "modified": "2017-09-27T12:38:18Z",
        "frozen": "2017-09-27T12:38:18Z",
        "size": 1024,
        "storage_service": "ida",
        "csc_project": "string",
        "checksum": "md5:string",
        "storage_identifier": "identifier",
        "user": "string",
    }
