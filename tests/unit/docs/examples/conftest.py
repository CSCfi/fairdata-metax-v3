import json
import os

import pytest

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/"


def load_test_json(filename):
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def v1_v3_dataset_v3_json():
    return load_test_json("v1-v3-dataset-v3.json")


@pytest.fixture
def v1_v3_data_catalog_v3_json():
    return load_test_json("v1-v3-data-catalog-v3.json")
