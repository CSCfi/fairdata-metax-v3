import json
import logging
import os
from pprint import pprint

import pytest

from apps.core.models import LegacyDataset

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "test_file_path, files_path, expected_diff",
    [
        (
            "dataset-harvested-fsd.json",
            None,
            {
                # Added items do not matter usually, as they are just artifacts from linking objects properly.
                # For example here creator is member of organization that gets additional identifier from database.
                # The identifier was not originally part of the v2 dataset organization description, but is added
                # as it is part of Organization object in v3.
                # "dictionary_item_added": [
                #    "root['research_dataset']['creator'][0]['member_of']['identifier']",
                #    "root['research_dataset']['creator'][1]['member_of']['identifier']",
                # ],
                # "dictionary_item_removed": [
                #     "root['research_dataset']['access_rights']['license'][0]['title']['und']"
                # ],
            },
        ),
        (
            "dataset-ida-files-qvain-created.json",
            "files-ida.json",
            {
                "dictionary_item_removed": [
                    # Some datasets in v1-v2 have theme, some have keyword in the research_dataset body.
                    # This can be resolved by preparing dataset before DeepDiff comparison, or writing custom operator
                    # for DeepDiff.
                    "root['research_dataset']['theme']",
                    # "root['research_dataset']['access_rights']['license'][0]['title']['und']",
                ]
            },
        ),
        (
            "dataset-remote-qvain-created.json",
            None,
            {
                "dictionary_item_added": [
                    # Not all datasets have total_files_byte_size field in v1-v2. The best way to pinpoint when it
                    # should be present in DeepDiff needs investigation.
                    "root['research_dataset']['total_files_byte_size']"
                ],
                "dictionary_item_removed": [
                    "root['research_dataset']['theme']",
                    # Project and funding integration should be completed in the adapter for is_output_of to work
                    # "root['research_dataset']['is_output_of']",
                    # Remote resources is not modeled yet
                    "root['research_dataset']['remote_resources']",
                    "root['research_dataset']['total_remote_resources_byte_size']",
                ],
            },
        ),
        (
            "dataset-remote-qvain-extra-contributor.json",
            None,
            {
                "dictionary_item_added": [
                    # Not all datasets have total_files_byte_size field in v1-v2. The best way to pinpoint when it
                    # should be present in DeepDiff needs investigation.
                    "root['research_dataset']['total_files_byte_size']"
                ],
                "dictionary_item_removed": [
                    "root['research_dataset']['theme']",
                    # Project and funding integration should be completed in the adapter for is_output_of to work
                    # "root['research_dataset']['is_output_of']",
                    # Remote resources is not modeled yet
                    "root['research_dataset']['remote_resources']",
                    "root['research_dataset']['total_remote_resources_byte_size']",
                ],
            },
        ),
    ],
)
@pytest.mark.adapter
@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion(
    license_reference_data, test_file_path, files_path, expected_diff
):
    # Data prep
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    data = None
    files_data = None
    with open(test_data_path + test_file_path) as json_file:
        data = json.load(json_file)
    if files_path:
        with open(test_data_path + files_path) as json_file:
            files_data = json.load(json_file)
    v2_dataset = LegacyDataset(dataset_json=data, files_json=files_data)

    v2_dataset.save()

    diff = v2_dataset.check_compatibility()

    assert diff == expected_diff
