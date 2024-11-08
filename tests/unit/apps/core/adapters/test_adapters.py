import copy
import json
import logging
import os
import uuid
from datetime import datetime
from pprint import pprint

import pytest
from rest_framework import serializers

from apps.core import factories
from apps.core.models import LegacyDataset
from apps.core.models.legacy_compatibility import LegacyCompatibility
from apps.files.models import File, FileStorage

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
                    "root['research_dataset']['total_files_byte_size']",
                ],
            },
        ),
        (
            "dataset-ida-files-qvain-created.json",
            "files-ida.json",
            {},
        ),
        (
            "dataset-remote-qvain-created.json",
            None,
            {
                "dictionary_item_removed": [
                    "root['research_dataset']['total_remote_resources_byte_size']",
                ],
            },
        ),
        (
            "dataset-remote-qvain-extra-contributor.json",
            None,
            {
                "dictionary_item_removed": [
                    "root['research_dataset']['total_remote_resources_byte_size']",
                ],
            },
        ),
    ],
)
@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion(
    data_catalog,
    data_catalog_att,
    funder_type_reference_data,
    license_reference_data,
    test_file_path,
    files_path,
    expected_diff,
):
    factories.ContractFactory(legacy_id=123)
    # Data prep
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    data = None
    file_ids = None
    with open(test_data_path + test_file_path) as json_file:
        data = json.load(json_file)
    if files_path:
        with open(test_data_path + files_path) as json_file:
            file_data = json.load(json_file)
            for f in file_data:
                File.create_from_legacy(f)
            file_ids = [f["id"] for f in file_data]

    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data, legacy_file_ids=file_ids)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    diff = LegacyCompatibility(v2_dataset).get_compatibility_diff()

    assert diff == expected_diff


@pytest.fixture
def harvested_json():
    test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"
    test_file_path = "dataset-harvested-fsd.json"
    with open(test_data_path + test_file_path) as json_file:
        return json.load(json_file)


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_invalid_identifier(harvested_json, license_reference_data):
    data = harvested_json
    # Cannot use non-UUID identifier
    data["identifier"] = "cr955e904-e3dd-4d7e-99f1-3fed446f96d1"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    with pytest.raises(serializers.ValidationError):
        v2_dataset.save()
        v2_dataset.update_from_legacy()


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_removed(harvested_json, license_reference_data):
    data = harvested_json
    data["removed"] = True
    data["date_removed"] = "2022-01-03T12:13:14Z"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    assert isinstance(v2_dataset.dataset.removed, datetime)


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_removed_restored(harvested_json, license_reference_data):
    data = harvested_json
    data["removed"] = False  # dataset has date_removed but is no longer removed
    data["date_removed"] = "2022-01-03T12:13:14Z"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    assert v2_dataset.dataset.removed is None


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_existing_v3_dataset_id(
    harvested_json, license_reference_data
):
    data = harvested_json
    # Cannot use identifier of an existing non-legacy V3 dataset
    dataset = factories.DatasetFactory()
    data["identifier"] = str(dataset.id)
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    with pytest.raises(serializers.ValidationError):
        v2_dataset.save()
        v2_dataset.update_from_legacy()


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_ignore_invalid_email(harvested_json, license_reference_data):
    data = harvested_json
    data["research_dataset"]["creator"][0]["email"] = "person@example;com"
    data["research_dataset"]["creator"][1]["email"] = "ok@example.com"
    data["research_dataset"]["creator"][2]["email"] = "org@example;com"
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    assert v2_dataset.invalid_legacy_values == {
        "research_dataset.creator[0]": {
            "error": "Invalid email",
            "fields": ["email"],
            "value": {
                "@type": "Person",
                "email": "person@example;com",
                "member_of": {"@type": "Organization", "name": {"en": "Aalto University"}},
                "name": "Mysterious Person",
            },
        },
        "research_dataset.creator[2]": {
            "error": "Invalid actor",
            "value": {
                "@type": "Organization",
                "email": "org@example;com",
                "name": {"en": "Aalto University"},
            },
        },
    }


def test_get_version_identifiers():
    dataset = factories.DatasetFactory()
    dataset2 = factories.DatasetFactory()
    dataset.dataset_versions.datasets.add(dataset2)
    assert dataset._get_version_identifiers() == sorted([str(dataset.id), str(dataset2.id)])

    # If dataset has no dataset_versions, dataset id should be returned
    dataset.dataset_versions.delete(soft=False)
    dataset.refresh_from_db()
    assert dataset.dataset_versions is None
    assert dataset._get_version_identifiers() == [str(dataset.id)]


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_draft_of(harvested_json, license_reference_data):
    data = harvested_json
    data_draft = copy.deepcopy(data)
    data_draft["identifier"] = str(uuid.UUID(int=123))
    data_draft["state"] = "draft"
    data_draft["research_dataset"]["preferred_identifier"] = "i am a draft"
    data_draft["draft_of"] = {"identifier": data["identifier"]}
    data["next_draft"] = {"identifier": data_draft["identifier"]}

    # Save original dataset first, draft assignment happens based on draft_of
    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()

    draft_dataset = LegacyDataset(id=data_draft["identifier"], dataset_json=data_draft)
    draft_dataset.save()
    draft_dataset.update_from_legacy()
    assert draft_dataset.dataset.draft_of == v2_dataset.dataset


@pytest.mark.django_db
def test_v2_to_v3_dataset_conversion_next_draft(harvested_json, license_reference_data):
    data = harvested_json
    data_draft = copy.deepcopy(data)
    data_draft["identifier"] = str(uuid.UUID(int=123))
    data_draft["state"] = "draft"
    data_draft["research_dataset"]["preferred_identifier"] = "i am a draft"
    data_draft["draft_of"] = {"identifier": data["identifier"]}
    data["next_draft"] = {"identifier": data_draft["identifier"]}

    # Save draft dataset first, draft assignment happens based on next_draft
    draft_dataset = LegacyDataset(id=data_draft["identifier"], dataset_json=data_draft)
    draft_dataset.save()
    draft_dataset.update_from_legacy()

    v2_dataset = LegacyDataset(id=data["identifier"], dataset_json=data)
    v2_dataset.save()
    v2_dataset.update_from_legacy()
    draft_dataset.dataset.refresh_from_db()
    assert draft_dataset.dataset.draft_of == v2_dataset.dataset
