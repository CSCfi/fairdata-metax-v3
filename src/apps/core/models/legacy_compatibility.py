import copy
import json
import logging
import re
from typing import Dict

import shapely
from deepdiff import DeepDiff, extract
from django.conf import settings
from django.utils.translation import gettext as _

from apps.common.helpers import omit_empty, parse_iso_dates_in_nested_dict, process_nested
from apps.core.models.legacy import LegacyDataset

logger = logging.getLogger(__name__)


def add_escapes(val: str):
    val = val.replace("[", "\\[")
    return val.replace("]", "\\]")


def regex(path: str):
    """Escape [ and ] and compile into regex."""
    return re.compile(add_escapes(path))


class LegacyCompatibility:
    """Helper class for legacy dataset compatibility checks."""

    def __init__(self, legacy_dataset: LegacyDataset) -> None:
        self.legacy_dataset = legacy_dataset

    ignored_migration_errors = {
        "dictionary_item_added": [
            "root['date_removed']",
            "root['research_dataset']['modified']",
            "root['research_dataset']['issued']",
            "root['metadata_owner_org']",  # Missing value filled from metadata_provider_org
            regex("root['research_dataset']['language'][\\d+]['title']"),
            regex("root['research_dataset']['spatial'][\\d+]['as_wkt']"),
            # Allow adding default "notspecified" license
            regex("root['research_dataset']['access_rights']['license'][\\d+]['identifier']"),
            regex("root['research_dataset']['access_rights']['license'][\\d+]['title']"),
        ],
        "dictionary_item_removed": [
            "root['next_draft']",  # Migrating drafts to V2 not supported
            "root['draft_of']",  # Migrating drafts to V2 not supported
            "root['user_created']",
            "root['previous_dataset_version']",
            "root['next_dataset_version']",
            "root['preservation_state']",
            "root['preservation_state_modified']",
            "root['preservation_description']",
            "root['preservation_reason_description']",
            "root['preservation_dataset_version']",
            "root['preservation_dataset_origin_version']",
            "root['preservation_identifier']",
            "root['research_dataset']['version_notes']",
            "root['research_dataset']['total_remote_resources_byte_size']",
            "root['research_dataset']['access_rights']['access_url']",
            "root['research_dataset']['files']",  # Uses separate V2 files API
            "root['research_dataset']['directories']",  # Uses separate V2 files API
            regex("root['research_dataset']['language'][\\d+]['title']['und']"),
            regex("root['research_dataset']['other_identifier'][\\d+]['old_notation']"),
            regex("root['research_dataset']['language'][\\d+]['title']['und']"),
            regex("root['research_dataset']['is_output_of'][\\d+]['homepage']"),
            regex(
                "root['research_dataset']['remote_resources'][\\d+]['has_object_characteristics']"
            ),
            regex("root['research_dataset']['remote_resources'][\\d+]['identifier']"),
            regex("root['research_dataset']['remote_resources'][\\d+]['access_url']['title']"),
            regex(
                "root['research_dataset']['remote_resources'][\\d+]['access_url']['description']"
            ),
            regex("root['research_dataset']['remote_resources'][\\d+]['download_url']['title']"),
            regex(
                "root['research_dataset']['remote_resources'][\\d+]['download_url']['description']"
            ),
            regex(".*['contributor_type']$"),
            regex(".*['contributor_role']$"),
            regex(".*['telephone']$"),
            regex(".*['definition']$"),  # remove silly definition values
            "root['contract']",  # TODO
            "root['editor_permissions']",  # TODO V3->V2
        ],
        "iterable_item_added": [
            regex("root['research_dataset']['spatial'][\\d+]['as_wkt'][\\d+]"),
        ],
        "values_changed": [
            regex(".*['spatial']([\\d+])?['as_wkt'][\\d+]"),
        ],
    }

    def match_ignore(self, value, ignored: list):
        for ign in ignored:
            if (isinstance(ign, str) and value == ign) or (
                isinstance(ign, re.Pattern) and ign.match(value)
            ):
                return True
        return False

    def should_ignore_removed(self, path) -> bool:
        """Allow removing None or [] dictionary values."""
        removed_value = extract(self.legacy_dataset.dataset_json, path)
        if path == "root['date_deprecated']":
            return not self.legacy_dataset.dataset_json.get("deprecated")
        elif path == "root['date_removed']":
            return not self.legacy_dataset.dataset_json.get("removed")
        elif path == "root['research_dataset']['total_files_byte_size']":
            return removed_value == 0
        if type(removed_value) is str:
            return removed_value.strip() == ""
        elif removed_value in [None, []]:
            return True
        return False

    def dot_path_to_deepdiff_path(self, path: str) -> str:
        """Convert javascript-style dot path to deepdiff style path.

        For example, `research_dataset.temporal[0].start_date`
        changes into `root['research_dataset']['temporal'][0]['start_date']`
        """
        parts = path.split(".")
        dd_parts = []
        for part in parts:
            dd_parts.append(re.sub(r"(^\w+)", r"['\1']", part))

        return "root" + "".join(dd_parts)

    def should_ignore_changed(self, path, new, old, fixed_paths) -> bool:
        if path in fixed_paths:
            return True  # Value has been fixed and we expected it to change

        if type(new) is dict and list(new) == ["as_wkt"]:
            return True  # Allow changes from normalizing as_wkt values

        if type(new) == type(old) == str and new == old.strip():
            return True  # Allow stripping whitespace

        if path == "root['research_dataset']['total_files_byte_size']":
            # Deprecated V2 dataset file size sometimes includes removed files and sometimes not
            if self.legacy_dataset.dataset.deprecated and old == 0 and new > 0:
                return True

    def get_migration_errors_from_diff(self, diff) -> dict:
        errors = {}
        fixed_paths = self.get_fixed_deepdiff_paths()
        for diff_type, diff in diff.items():
            ignored = self.ignored_migration_errors.get(diff_type, [])
            for value in diff:
                if self.match_ignore(value, ignored):
                    continue

                if diff_type == "dictionary_item_removed" and self.should_ignore_removed(value):
                    continue

                if diff_type == "values_changed":
                    new = diff[value]["new_value"]
                    old = diff[value]["old_value"]
                    if self.should_ignore_changed(value, new, old, fixed_paths):
                        continue

                if isinstance(diff, dict):
                    errors.setdefault(diff_type, []).append(f"{value}={diff[value]}")
                else:
                    errors.setdefault(diff_type, []).append(f"{value}")

        return errors

    def normalize_float_str(self, value: str) -> str:
        """Limit number of significant digits for float value in string."""
        try:
            value = float(value)
            value = f"{value:.8g}"
        except ValueError:
            pass
        return value

    def normalize_dataset(self, data: dict) -> dict:
        """Process dataset json dict to avoid unnecessary diff values."""

        invalid = self.legacy_dataset.invalid_legacy_values or {}

        wkt_re = re.compile(r".*as_wkt\[\d+\]$")
        from apps.core.models import Dataset

        data["state"] = str(data["state"])  # Convert Dataset.StateChoices to str

        def pre_handler(value, path):
            if inv := invalid.get(path):
                # Remove invalid values from comparison
                if fields := inv.get("fields"):
                    return {  # Remove invalid fields
                        k: v for k, v in value.items() if k not in fields
                    }
                else:
                    return None  # Remove entire object
            if type(value) is str:
                value = value.strip()
                if wkt_re.match(path):
                    # Normalize wkt
                    value = shapely.wkt.dumps(shapely.wkt.loads(value), rounding_precision=4)
                elif path.endswith(".alt"):
                    # Normalize altitude values
                    value = self.normalize_float_str(value)
                # Remove leading and trailing whitespace
                return value
            elif isinstance(value, dict):
                # Omit empty values from dict
                return omit_empty(value)
            return value

        def post_handler(value, path):
            """Remove None values."""
            if isinstance(value, list):
                value = [v for v in value if v is not None]
                if not value:
                    return None
            if isinstance(value, dict):
                value = {k: v for k, v in value.items() if v is not None}
                if not value:
                    return None

            return value

        data = copy.deepcopy(data)
        data["research_dataset"] = process_nested(
            data.get("research_dataset"), pre_handler, post_handler, path="research_dataset"
        )
        return parse_iso_dates_in_nested_dict(data)

    def exclude_from_diff(self, obj, path: str):
        if isinstance(obj, dict):
            identifier = obj.get("identifier") or ""
            if identifier.startswith(settings.ORGANIZATION_BASE_URI):
                # Assume object is a reference data organization
                return True
            if path.endswith("['definition']"):
                # Ignore silly definition values
                en = obj.get("en", "")
                return "statement or formal explanation of the meaning of a concept" in en

        return False

    def get_fixed_deepdiff_paths(self) -> list:
        """Get deepdiff paths to values that have been fixed in the migration conversion."""
        fixed = self.legacy_dataset.fixed_legacy_values or {}
        fixed_paths = []
        for path, val in fixed.items():
            fields = val.get("fields", [])
            if fields:
                fixed_paths.extend(f"{path}.{field}" for field in fields)
            else:
                fixed_paths.append(path)

        return [self.dot_path_to_deepdiff_path(p) for p in fixed_paths]

    def get_file_count_changes(self) -> dict:
        """Check if migrated file and file metadata counts match."""
        research_dataset = self.legacy_dataset.legacy_research_dataset
        v2_file_count = 0
        v2_file_metadata_count = len(research_dataset.get("files") or [])
        v2_directory_metadata_count = len(research_dataset.get("directories") or [])
        if legacy_ids := self.legacy_dataset.legacy_file_ids:
            v2_file_count = len(legacy_ids)

        v3_file_count = 0
        v3_file_metadata_count = 0
        v3_directory_metadata_count = 0
        if fileset := getattr(self.legacy_dataset.dataset, "file_set", None):
            v3_file_count = fileset.total_files_count
            v3_file_metadata_count = fileset.file_metadata.count()
            v3_directory_metadata_count = fileset.directory_metadata.count()

        ret = {}
        if v2_file_count != v3_file_count:
            ret["file_count_changed"] = {"old_value": v2_file_count, "new_value": v3_file_count}
        if v2_file_metadata_count != v3_file_metadata_count:
            ret["file_metadata_count_changed"] = {
                "old_value": v2_file_metadata_count,
                "new_value": v3_file_metadata_count,
            }
        if v2_directory_metadata_count != v3_directory_metadata_count:
            ret["directory_metadata_count_changed"] = {
                "old_value": v2_directory_metadata_count,
                "new_value": v3_directory_metadata_count,
            }
        return ret

    def get_compatibility_diff(self) -> Dict:
        v2_version = self.normalize_dataset(self.legacy_dataset.dataset_json)
        v3_version = self.normalize_dataset(self.legacy_dataset.dataset.as_v2_dataset())

        diff = DeepDiff(
            v2_version,
            v3_version,
            ignore_order=True,
            cutoff_intersection_for_pairs=1.0,
            cutoff_distance_for_pairs=1.0,
            exclude_paths=[
                "id",
                "service_modified",
                "service_created",
                "use_doi_for_published",  # Should be `null` in V2 for published datasets but isn't always
                "root['data_catalog']['id']",
                "root['research_dataset']['metadata_version_identifier']",
                "root['dataset_version_set']",  # not directly writable
                "root['alternate_record_set']",  # list of records sharing same preferred_identifier
                "date_modified",  # modification date is always set in V3
            ],
            exclude_regex_paths=[
                # old_notation is related to a SYKE migration in 2020, not relevant anymore
                add_escapes("^root['research_dataset']['other_identifier'][\\d+]['old_notation']"),
                # reference data labels may have differences
                add_escapes("['pref_label']$"),
                add_escapes("^root['research_dataset']['language'][\\d+]['title']"),
                add_escapes(
                    "^root['research_dataset']['access_rights']['license'][\\d+]['title']['und']"
                ),
            ],
            truncate_datetime="day",
            exclude_obj_callback=self.exclude_from_diff,
        )
        json_diff = diff.to_json()
        output = json.loads(json_diff)
        output.update(self.get_file_count_changes())
        return output
