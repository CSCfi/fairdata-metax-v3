import json
import logging
import os
from datetime import datetime
from pprint import pprint

import pytest
from rest_framework import serializers

from apps.core import factories
from apps.core.models import LegacyDataset
from apps.core.models.legacy_compatibility import LegacyCompatibility

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.adapter]


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
                "dictionary_item_added": ["root['research_dataset']['issued']"],
                "dictionary_item_removed": [
                    "root['preservation_state']",
                    "root['research_dataset']['total_files_byte_size']",
                ],
            },
        ),
        (
            "dataset-ida-files-qvain-created.json",
            "files-ida.json",
            {
                "dictionary_item_removed": [
                    "root['preservation_state']",
                    "root['preservation_identifier']",
                ],
            },
        ),
        (
            "dataset-remote-qvain-created.json",
            None,
            {
                "dictionary_item_removed": [
                    "root['preservation_state']",
                    "root['research_dataset']['total_remote_resources_byte_size']",
                ],
            },
        ),
        (
            "dataset-remote-qvain-extra-contributor.json",
            None,
            {
                "dictionary_item_removed": [
                    "root['preservation_state']",
                    "root['research_dataset']['total_remote_resources_byte_size']",
                ],
            },
        ),
    ],
)
@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion(
    data_catalog,
    funder_type_reference_data,
    license_reference_data,
    test_file_path,
    files_path,
    expected_diff,
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

    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data, files_json=files_data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    diff = LegacyCompatibility(v2_dataset).get_compatibility_diff()

    assert diff == expected_diff


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_invalid_identifier(license_reference_data):
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    test_file_path = "dataset-harvested-fsd.json"
    data = None
    with open(test_data_path + test_file_path) as json_file:
        data = json.load(json_file)

    # Cannot use non-UUID identifier
    data["identifier"] = "cr955e904-e3dd-4d7e-99f1-3fed446f96d1"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    with pytest.raises(serializers.ValidationError):
        v2_dataset.save()
        v2_dataset.update_from_legacy()


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_removed(license_reference_data):
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    test_file_path = "dataset-harvested-fsd.json"
    data = None
    with open(test_data_path + test_file_path) as json_file:
        data = json.load(json_file)

    data["removed"] = True
    data["date_removed"] = "2022-01-03T12:13:14Z"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    assert isinstance(v2_dataset.removed, datetime)


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_removed_restored(license_reference_data):
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    test_file_path = "dataset-harvested-fsd.json"
    data = None
    with open(test_data_path + test_file_path) as json_file:
        data = json.load(json_file)

    data["removed"] = False  # dataset has date_removed but is no longer removed
    data["date_removed"] = "2022-01-03T12:13:14Z"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    assert v2_dataset.removed is None


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_existing_v3_dataset_id(license_reference_data):
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    test_file_path = "dataset-harvested-fsd.json"
    data = None
    with open(test_data_path + test_file_path) as json_file:
        data = json.load(json_file)

    # Cannot use identifier of an existing non-legacy V3 dataset
    dataset = factories.DatasetFactory()
    data["identifier"] = str(dataset.id)
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    with pytest.raises(serializers.ValidationError):
        v2_dataset.save()
        v2_dataset.update_from_legacy()
