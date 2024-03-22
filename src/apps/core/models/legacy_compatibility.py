import copy
import json
import logging
import re
from typing import Dict

from deepdiff import DeepDiff, extract
from django.conf import settings
from django.utils.translation import gettext as _

from apps.common.helpers import parse_iso_dates_in_nested_dict, trim_nested_dict
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

    def __init__(self, dataset: LegacyDataset) -> None:
        self.dataset = dataset

    ignored_migration_errors = {
        "dictionary_item_added": [
            "root['research_dataset']['modified']",
            "root['research_dataset']['issued']",
            regex("root['research_dataset']['language'][\\d+]['title']"),
            regex("root['research_dataset']['spatial'][\\d+]['as_wkt']"),
            # Allow adding default "notspecified" license
            regex("root['research_dataset']['access_rights']['license'][\\d+]['identifier']"),
            regex("root['research_dataset']['access_rights']['license'][\\d+]['title']"),
        ],
        "dictionary_item_removed": [
            "root['user_created']",
            "root['previous_dataset_version']",
            "root['next_dataset_version']",
            "root['preservation_state']",
            "root['preservation_state_modified']",
            "root['preservation_description']",
            "root['preservation_reason_description']",
            "root['preservation_dataset_version']",
            "root['preservation_identifier']",
            "root['research_dataset']['version_notes']",
            "root['research_dataset']['total_files_byte_size']",
            "root['research_dataset']['total_remote_resources_byte_size']",
            regex("root['research_dataset']['language'][\\d+]['title']['und']"),
            regex("root['research_dataset']['other_identifier'][\\d+]['old_notation']"),
            regex("root['research_dataset']['language'][\\d+]['title']['und']"),
            regex("root['research_dataset']['is_output_of'][\\d+]['homepage']"),
            regex(".*['contributor_role']$"),
            "root['contract']", # TODO
        ],
        "iterable_item_added": [
            regex("root['research_dataset']['spatial'][\\d+]['as_wkt'][\\d+]"),
        ],
        "values_changed": [
            regex("root['research_dataset']['spatial'][\\d+]['as_wkt'][\\d+]"),
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
        removed_value = extract(self.dataset.dataset_json, path)
        if removed_value in [None, []]:
            return True
        return False

    def should_ignore_changed(self, path, new, old) -> bool:
        if list(new) == ["as_wkt"]:
            return True  # Allow changes from normalizing as_wkt values

        if type(new) == type(old) == str and new == old.strip():
            return True  # Allow stripping whitespace

    def get_migration_errors_from_diff(self, diff) -> dict:
        errors = {}
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
                    if self.should_ignore_changed(value, new, old):
                        continue

                if isinstance(diff, dict):
                    errors.setdefault(diff_type, []).append(f"{value}={diff[value]}")
                else:
                    errors.setdefault(diff_type, []).append(f"{value}")

        return errors

    def normalize_dict(self, data):
        return trim_nested_dict(parse_iso_dates_in_nested_dict(copy.deepcopy(data)))

    def exclude_from_diff(self, obj, path):
        if isinstance(obj, dict):
            identifier = obj.get("identifier") or ""
            if identifier.startswith(settings.ORGANIZATION_BASE_URI):
                # Assume object is a reference data organization
                return True
        return False

    def get_compatibility_diff(self) -> Dict:
        v3_version = self.normalize_dict(self.dataset.as_v2_dataset())
        v2_version = self.normalize_dict(self.dataset.dataset_json)
        diff = DeepDiff(
            v2_version,
            v3_version,
            ignore_order=True,
            cutoff_intersection_for_pairs=1.0,
            cutoff_distance_for_pairs=1.0,
            exclude_paths=[
                "id",
                "api_meta",
                "service_modified",
                "service_created",
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
            exclude_obj_callback_strict=self.exclude_from_diff,
        )
        json_diff = diff.to_json()
        return json.loads(json_diff)
