import json

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_create_dataset_default_timestamps(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert parse_datetime(res.data["created"]) < timezone.now()
    assert parse_datetime(res.data["modified"]) < timezone.now()


def test_create_dataset_with_timestamps(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json['created'] = "2018-05-17T10:11:12Z"
    dataset_a_json['modified'] = "2020-05-17T10:11:12Z"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["created"] < res.data["modified"]


def test_create_dataset_with_wrong_timestamps(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json['created'] = "2021-05-17T10:11:12Z"
    dataset_a_json['modified'] = "2020-05-17T10:11:12Z"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400


def test_create_dataset_with_created_timestamp(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json['created'] = "2018-05-17T10:11:12Z"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["created"] == "2018-05-17T10:11:12Z"
    assert res.data["created"] < res.data["modified"]
    assert parse_datetime(res.data["modified"]) < timezone.now()


def test_create_dataset_with_modified_timestamp(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["modified"] = "2018-05-17T10:11:12Z"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400


def test_create_dataset_future_timestamps(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["modified"] = "2100-05-17T10:11:12Z"
    dataset_a_json["created"] = "2100-02-17T10:11:12Z"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert len(res.data) == 2

    dataset_a_json["modified"] = "2023-10-12T09:57:06.194633+03:00"
    dataset_a_json["created"] = "2023-10-12T06:57:06.194633+00:00"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


def test_create_dataset_change_timestamps(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["created"] = "2018-05-17T10:11:12Z"
    dataset_a_json["modified"] = "2020-05-17T10:11:12Z"
    dataset_a_json["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res.data.pop("fileset")
    res.data.pop("metadata_owner")
    res.data.pop("preservation")
    dataset_id = res.data["id"]
    res.data["created"] = "2016-05-17T10:11:12Z"
    res.data["modified"] = "2019-05-17T10:11:12Z"
    res = admin_client.put(f"/v3/datasets/{dataset_id}", res.data, content_type="application/json")
    assert res.status_code == 200
    assert res.data["created"] < res.data["modified"]
    assert res.data["created"] == "2018-05-17T10:11:12Z"
    assert res.data['modified'] == "2019-05-17T10:11:12Z"
