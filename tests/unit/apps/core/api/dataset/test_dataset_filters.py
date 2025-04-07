import datetime
import logging

import pytest
from django.utils.http import http_date
from tests.utils import assert_nested_subdict

from apps.core import factories
from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def ida_dataset(data_catalog, reference_data):
    ida_storage = factories.FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = factories.DatasetFactory(data_catalog=data_catalog)
    factories.FileSetFactory(dataset=dataset, storage=ida_storage)
    return dataset


@pytest.fixture
def ida_dataset_other(data_catalog, reference_data):
    ida_storage = factories.FileStorageFactory(storage_service="ida", csc_project="other_project")
    dataset = factories.DatasetFactory(data_catalog=data_catalog)
    factories.FileSetFactory(dataset=dataset, storage=ida_storage)
    return dataset


@pytest.fixture
def pas_dataset(data_catalog, reference_data):
    pas_storage = factories.FileStorageFactory(storage_service="pas", csc_project="project")
    dataset = factories.DatasetFactory(data_catalog=data_catalog)
    factories.FileSetFactory(dataset=dataset, storage=pas_storage)
    return dataset


def test_filter_pid(
    admin_client, dataset_a_json, dataset_b_json, datacatalog_harvested_json, reference_data
):
    dataset_a_json["generate_pid_on_publish"] = None
    dataset_b_json["generate_pid_on_publish"] = None
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json["persistent_identifier"] = "other_pid"
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_b_json["data_catalog"] = datacatalog_harvested_json["id"]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201, res.data
    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.get("/v3/datasets?persistent_identifier=some_pid")
    assert res.data["count"] == 1


def test_search_pid(
    admin_client, dataset_a_json, dataset_b_json, datacatalog_harvested_json, reference_data
):
    dataset_a_json["generate_pid_on_publish"] = None
    dataset_b_json["generate_pid_on_publish"] = None
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json["persistent_identifier"] = "anotherpid"
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_b_json["data_catalog"] = datacatalog_harvested_json["id"]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.get("/v3/datasets?search=some_pid")
    assert res.data["count"] == 1


def test_search_phrase(admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    dataset_a_json["title"] = {"en": "Testidatasetti X has a title x y"}
    dataset_b_json["title"] = {"en": "Testidatasetti Y has a title x y"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.get("/v3/datasets?search=testidatasetti x has")
    assert res.data["count"] == 2
    res = admin_client.get('/v3/datasets?search="testidatasetti x has"')
    assert res.data["count"] == 1


def test_aggregation_and_filters(
    admin_client, dataset_a_json, dataset_b_json, dataset_c_json, data_catalog, reference_data
):
    admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_c_json, content_type="application/json")
    res = admin_client.get("/v3/datasets")
    assert res.data["count"] == 3

    res = admin_client.get("/v3/datasets/aggregates")
    assert res.data != None
    assert sorted(res.data.keys()) == [
        "access_type",
        "creator",
        "data_catalog",
        "field_of_science",
        "file_type",
        "infrastructure",
        "keyword",
        "organization",
        "project",
    ]
    aggregates = res.data

    for aggregate in aggregates.values():
        if len(aggregate["hits"]):
            value = (
                aggregate["hits"][0]["value"].get("fi")
                or aggregate["hits"][0]["value"].get("en")
                or aggregate["hits"][0]["value"].get("und")
            )
            count = aggregate["hits"][0]["count"]
            print(f"{aggregate['query_parameter']}, {value}, {count}")
            res = admin_client.get(f"/v3/datasets?{aggregate['query_parameter']}={value}")
            assert res.data["count"] == count


def test_aggregation_query_params(user_client):
    factories.PublishedDatasetFactory(title={"en": "apples"}, keyword=["fruit"])
    factories.PublishedDatasetFactory(title={"en": "bananas"}, keyword=["fruit"])

    # No params, includes all published datasets
    res = user_client.get("/v3/datasets/aggregates")
    assert res.status_code == 200
    assert res.data["keyword"]["hits"] == [{"value": {"und": "fruit"}, "count": 2}]

    # Includes only results matching dataset filtering query params
    res = user_client.get("/v3/datasets/aggregates?title=apple")
    assert res.status_code == 200
    assert res.data["keyword"]["hits"] == [{"value": {"und": "fruit"}, "count": 1}]


def test_aggregation_query_params_invalid(user_client):
    res = user_client.get("/v3/datasets/aggregates?schtitle=apple")
    assert res.status_code == 400
    assert res.json() == {"schtitle": "Unknown query parameter"}


def test_list_datasets_with_ordering(
    admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_a_id = res.data["id"]
    dataset_a_pid = res.data["persistent_identifier"]
    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    dataset_a_json["persistent_identifier"] = dataset_a_pid
    res = admin_client.put(
        f"/v3/datasets/{dataset_a_id}",
        dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200, res.data
    res = admin_client.get("/v3/datasets?ordering=created")
    assert_nested_subdict(
        {0: dataset_a_json, 1: dataset_b_json},
        dict(enumerate((res.data["results"]))),
        ignore=["generate_pid_on_publish"],
    )

    res = admin_client.get("/v3/datasets?ordering=modified")
    assert_nested_subdict(
        {0: dataset_b_json, 1: dataset_a_json},
        dict(enumerate((res.data["results"]))),
        ignore=["generate_pid_on_publish"],
    )


def test_list_datasets_with_if_modified_since_header(
    admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res_a = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")

    res_b = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")

    modified_since_time = http_date(datetime.datetime.now(datetime.timezone.utc).timestamp())
    modified_a = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=12)
    modified_b = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)
    print(f"{modified_since_time=}")
    print(f"modified_a={modified_a}")
    print(f"modified_b={modified_b}")

    dataset_a_id = res_a.data.get("id")
    dataset_b_id = res_b.data.get("id")

    dataset_a = Dataset.objects.get(id=dataset_a_id)
    dataset_b = Dataset.objects.get(id=dataset_b_id)

    Dataset.objects.filter(id=dataset_a.id).update(modified=modified_a)

    Dataset.objects.filter(id=dataset_b.id).update(modified=modified_b)

    res = admin_client.get(
        "/v3/datasets", content_type="application/json", HTTP_IF_MODIFIED_SINCE=modified_since_time
    )
    assert_nested_subdict(
        {0: dataset_a_json},
        dict(enumerate((res.data["results"]))),
        ignore=["generate_pid_on_publish"],
    )


def test_list_datasets_with_bad_if_modified_since_header(
    admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")

    modified_since_time = "not good"

    res = admin_client.get(
        "/v3/datasets", content_type="application/json", HTTP_IF_MODIFIED_SINCE=modified_since_time
    )
    assert res.status_code == 400
    assert res.json() == {
        "headers": {
            "If-Modified-Since": "Bad value. If-Modified-Since supports only RFC 2822 datetime format."
        }
    }


def test_owned_dataset(
    admin_client, user_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    """End-user cannot use custom metadata owner values."""
    dataset_a_json["state"] = "published"
    dataset_b_json["state"] = "published"
    dataset_b_json["actors"] = [
        {"roles": ["creator", "publisher"], "organization": {"pref_label": {"en": "org"}}}
    ]
    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_id = res.data["id"]
    assert res.status_code == 201

    res = user_client.get(
        "/v3/datasets?only_owned_or_shared=false", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["count"] == 2

    res = user_client.get(
        "/v3/datasets?only_owned_or_shared=true", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["id"] == dataset_id


def test_filter_by_storage_service(admin_client, ida_dataset, ida_dataset_other, pas_dataset):
    res = admin_client.get(
        "/v3/datasets?storage_services=ida&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(ida_dataset.id), str(ida_dataset_other.id)}

    res = admin_client.get(
        "/v3/datasets?storage_services=pas&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(pas_dataset.id)}

    res = admin_client.get(
        "/v3/datasets?storage_services=ida,pas&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {
        str(pas_dataset.id),
        str(ida_dataset.id),
        str(ida_dataset_other.id),
    }


def test_filter_by_csc_project(admin_client, ida_dataset, ida_dataset_other, pas_dataset):
    res = admin_client.get(
        "/v3/datasets?csc_projects=project&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(ida_dataset.id), str(pas_dataset.id)}

    res = admin_client.get(
        "/v3/datasets?csc_projects=other_project&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(ida_dataset_other.id)}

    res = admin_client.get(
        "/v3/datasets?csc_projects=project,other_project&pagination=false",
        content_type="application/json",
    )
    assert {d["id"] for d in res.data} == {
        str(pas_dataset.id),
        str(ida_dataset.id),
        str(ida_dataset_other.id),
    }


def test_filter_by_has_files(
    admin_client, dataset_a, dataset_with_files, data_catalog, reference_data
):
    res = admin_client.get(
        "/v3/datasets?has_files=false&pagination=false", content_type="application/json"
    )
    assert [d["id"] for d in res.data] == [dataset_a.dataset_id]
    res = admin_client.get(
        "/v3/datasets?has_files=true&pagination=false", content_type="application/json"
    )
    assert [d["id"] for d in res.data] == [str(dataset_with_files.id)]


def test_filter_by_organization_name(admin_client, dataset_a, data_catalog, reference_data):
    main_org = factories.OrganizationFactory(pref_label={"en": "Mainorg"})
    sub_org = factories.OrganizationFactory(pref_label={"en": "Suborg"}, parent=main_org)
    sub_sub_org = factories.OrganizationFactory(pref_label={"en": "Subsuborg"}, parent=sub_org)
    actor = factories.DatasetActorFactory(organization=sub_sub_org)
    dataset = factories.DatasetFactory()
    dataset.actors.set([actor])
    res = admin_client.get(
        "/v3/datasets?actors__organization__pref_label=Subsuborg&pagination=false",
        content_type="application/json",
    )
    assert [d["id"] for d in res.data] == [str(dataset.id)]

    res = admin_client.get(
        "/v3/datasets?actors__organization__pref_label=Suborg&pagination=false",
        content_type="application/json",
    )
    assert [d["id"] for d in res.data] == [str(dataset.id)]

    res = admin_client.get(
        "/v3/datasets?actors__organization__pref_label=Mainorg&pagination=false",
        content_type="application/json",
    )
    assert [d["id"] for d in res.data] == [str(dataset.id)]


def test_filter_by_id(admin_client, dataset_a, dataset_b, dataset_c):
    dataset_id = str(Dataset.objects.first().id)

    res = admin_client.get(
        f"/v3/datasets?id={dataset_id}&pagination=false", content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["id"] == dataset_id


def test_filter_by_invalid_id(admin_client):
    res = admin_client.get("/v3/datasets?id=123&pagination=false", content_type="application/json")
    assert res.status_code == 400
    assert res.json() == {"id": "Dataset identifiers must be valid UUIDs. Invalid IDs: ['123']"}


def test_filter_by_multiple_ids(admin_client, dataset_a, dataset_b, dataset_c):
    ids = sorted([str(d.id) for d in Dataset.objects.all()[:2]])
    res = admin_client.get(
        f"/v3/datasets?id={','.join(ids)}&pagination=false", content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data) == 2
    assert sorted([d["id"] for d in res.data]) == ids
