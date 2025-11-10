import logging

import requests

from dpres_file_formats import __version__ as DPRES_FILE_FORMATS_VERSION
from dpres_file_formats.read_file_formats import file_formats as get_file_formats

from apps.refdata.services.importers.common import BaseDataImporter

_logger = logging.getLogger(__name__)


class DPRESFileFormatVersionImporter(BaseDataImporter):
    """
    Importer for DPRES file format version using dpres-file-formats Python
    library
    """
    def get_data(self):
        _logger.info(
            f"Downloading file format version data from {self.source}"
        )

        response = requests.get(
            self.source,
            headers={
                "User-Agent": \
                    "fairdata-metax-v3 (github.com/CSCfi/fairdata-metax-v3)"
            }
        )
        response.raise_for_status()
        data = response.json()

        if "file_formats" not in data:
            _logger.error(
                "Received JSON does not contain 'file_formats' field, "
                "skipping."
            )
            return None

        _logger.info(
            f"Parsing data using dpres-file-formats "
            f"v{DPRES_FILE_FORMATS_VERSION}"
        )

        # Dict is used as dpres-file-formats might list some formats twice
        # with a differing `content_type`
        id2file_format = {}

        file_formats = get_file_formats(data=data, unofficial=True)

        for file_format in file_formats:
            mime = file_format["mimetype"]
            version = file_format["version"].replace("(:unap)", "")

            id_ = f"{mime.replace('/', '_').replace(' ', '_').lower()}"
            if version:
                id_ += f"_{version.replace(' ', '_').replace('(:unkn)', 'unkn')}"

            label = " ".join(filter(None, [mime, version]))

            id2file_format[id_] = {
                "url": f"http://uri.suomi.fi/codelist/fairdata/file_format_version/code/{id_}",
                "format_version": version,
                "file_format": mime,
                "pref_label": {
                    "en": label,
                    "fi": label,
                    "und": label
                },

                "broader": [],
                "same_as": [],
                "deprecated": None
            }

        # Return a list of unique file formats
        return list(id2file_format.values())
