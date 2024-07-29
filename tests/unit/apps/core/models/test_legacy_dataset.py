import pytest

from apps.core.models import LegacyDataset

pytestmark = [pytest.mark.adapter]


def test_legacy_dataset_api_version():
    dataset_json_without_version = {
        "research_dataset": {"title": {"en": "Hello"}},
        "metadata_provider_user": "test_user",
        "metadata_provider_org": "test_org",
    }

    # By default, API version comes from dataset_json
    dataset_json = {"api_meta": {"version": 2}, **dataset_json_without_version}
    d = LegacyDataset(dataset_json=dataset_json)
    assert d.api_version == 2
    assert d.title == {"en": "Hello"}

    # Default API version 1 if not in json
    d = LegacyDataset(dataset_json=dataset_json_without_version)
    assert d.api_version == 1
    assert d.title == {"en": "Hello"}

    # Respect API version from kwargs
    d = LegacyDataset(dataset_json=dataset_json, api_version=712)
    assert d.api_version == 712
    assert d.title == {"en": "Hello"}

    # Respect API version from args
    opts = LegacyDataset._meta
    args = [None] * len(opts.concrete_fields)
    args[opts.concrete_fields.index(opts.get_field("dataset_json"))] = dataset_json
    args[opts.concrete_fields.index(opts.get_field("api_version"))] = 1337
    d = LegacyDataset(*args)
    assert d.api_version == 1337
    assert d.title == {"en": "Hello"}
