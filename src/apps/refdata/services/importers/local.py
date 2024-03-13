import json
import logging

from apps.refdata.services.importers.common import BaseDataImporter

_logger = logging.getLogger(__name__)


class LocalJSONImporter(BaseDataImporter):
    """Importer for generic reference data from local json file."""

    def data_item_from_json(self, json_item):
        return {
            "url": json_item["uri"],
            "in_scheme": json_item.get("scheme", ""),
            "pref_label": json_item.get("label", ""),
            "broader": [],
            "same_as": json_item.get("same_as", []),
            "deprecated": None,
        }

    def get_data(self):
        _logger.info(f"Loading data from {self.source}")

        items = []
        with open(self.source) as f:
            items = json.load(f)

        data = [self.data_item_from_json(item) for item in items]
        return data


class LocalJSONFileFormatVersionImporter(LocalJSONImporter):
    """Importer for file format version data from local json."""

    def data_item_from_json(self, json_item):
        item = super().data_item_from_json(json_item)
        file_format = json_item["input_file_format"]
        format_version = json_item["output_format_version"]
        label = " ".join(filter(None, [file_format, format_version]))
        item.update(
            {
                "file_format": file_format,
                "format_version": format_version,
                "pref_label": {
                    "en": label,
                    "fi": label,
                    "und": label,
                },
            }
        )
        return item


class LocalJSONLicenseImporter(LocalJSONImporter):
    """Importer for license data from local json."""

    def data_item_from_json(self, json_item):
        item = super().data_item_from_json(json_item)
        return item
