import datetime
import logging

import pytest
from rest_framework.reverse import reverse
from tests.utils import matchers

from apps.core.models import DataCatalog

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.datacatalog,
    pytest.mark.usefixtures("language_reference_data"),
]


def test_create_datacatalog(admin_client, datacatalog_a_json, data_catalog_list_url):
    res = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    logger.info(str(res.data))
    assert res.status_code == 201


def test_create_minimal_datacatalog(admin_client, datacatalog_d_json, data_catalog_list_url):
    res = admin_client.post(
        data_catalog_list_url, datacatalog_d_json, content_type="application/json"
    )
    logger.info(str(res.data))
    assert res.status_code == 201


def test_create_datacatalog_twice(admin_client, datacatalog_a_json, data_catalog_list_url):
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res1.status_code == 201
    res2 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res2.status_code == 400


def test_change_datacatalog(
    admin_client, datacatalog_c_json, datacatalog_put_json, data_catalog_list_url
):
    _now = datetime.datetime.now()

    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_c_json, content_type="application/json"
    )
    datacatalog_put_json["id"] = datacatalog_c_json["id"]
    response = admin_client.put(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-uusitesti'])}",
        datacatalog_put_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    logger.info(str(response.data))
    assert len(response.data.get("language")) == 2


def test_change_datacatalog_id(
    admin_client, datacatalog_c_json, datacatalog_put_json, data_catalog_list_url
):
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_c_json, content_type="application/json"
    )
    response = admin_client.patch(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-uusitesti'])}",
        {"id": "i'm changing id"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "cannot be changed for an existing data catalog" in response.json()["id"]


def test_change_datacatalog_to_minimal(
    admin_client, datacatalog_a_json, datacatalog_d_json, data_catalog_list_url
):
    _now = datetime.datetime.now()
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    response = admin_client.put(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-testi'])}",
        datacatalog_d_json,
        content_type="application/json",
    )
    assert response.status_code == 200


def test_change_datacatalog_from_minimal(
    admin_client, datacatalog_a_json, datacatalog_d_json, data_catalog_list_url
):
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_d_json, content_type="application/json"
    )
    response = admin_client.put(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-testi'])}",
        datacatalog_a_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    logger.info(f"{response.data=}")
    assert response.data.get("language")[0].get("url") == "http://lexvo.org/id/iso639-3/fin"


def test_create_datacatalog_error(admin_client, datacatalog_error_json, data_catalog_list_url):
    res = admin_client.post(
        data_catalog_list_url, datacatalog_error_json, content_type="application/json"
    )
    assert res.status_code == 400


@pytest.mark.auth
def test_datacatalog_permissions(
    requests_client,
    live_server,
    reference_data,
    data_catalog_list_url,
    end_users,
    service_user,
    update_request_client_auth_token,
    datacatalog_a_json,
    datacatalog_c_json,
    datacatalog_put_json,
):
    user1, user2, user3 = end_users
    list_endpoint = data_catalog_list_url
    url = f"{live_server.url}{list_endpoint}"

    # service user can create data-catalog
    update_request_client_auth_token(requests_client, service_user.token)
    res1 = requests_client.post(url, json=datacatalog_a_json)
    assert res1.status_code == 201

    detail_endpoint = reverse("datacatalog-detail", args=[res1.json()["id"]])
    detail_url = f"{live_server.url}{detail_endpoint}"

    # service user can modify data-catalog
    res2 = requests_client.put(detail_url, json=datacatalog_put_json)
    assert res2.status_code == 200

    # end-user can not create or modify data-catalog
    update_request_client_auth_token(requests_client, user1.token)
    res3 = requests_client.post(url, json=datacatalog_c_json)
    assert res3.status_code == 403

    res4 = requests_client.put(detail_url, json=datacatalog_put_json)
    assert res4.status_code == 403

    # end-user can not delete data-catalog
    res5 = requests_client.delete(detail_url)
    assert res5.status_code == 403

    # service user can delete data-catalog
    update_request_client_auth_token(requests_client, service_user.token)
    res6 = requests_client.delete(detail_url)
    assert res6.status_code == 204


def test_list_datacatalogs(admin_client, post_datacatalog_payloads_a_b_c, data_catalog_list_url):
    response = admin_client.get(data_catalog_list_url)
    logger.info(f"{response.data=}")
    catalog_count = DataCatalog.available_objects.all().count()
    assert response.status_code == 200
    assert response.data.get("count") == catalog_count


@pytest.mark.parametrize(
    "catalog_filter, filter_value, filter_result",
    [
        ("is_external", True, 1),
        ("dataset_versioning_enabled", True, 1),
        ("dataset_versioning_enabled", False, 2),
        ("title", "katalogi", 3),
        ("title", "New", 1),
        ("id", "nbn:fi:att", 3),
        ("description", "repo", 2),
        ("publisher__name", "testi", 3),
        ("publisher__homepage__url", ".fi", 3),
        ("publisher__homepage__title", "website", 3),
        ("language__url", "lexvo.org", 3),
        ("language__pref_label", "englannin kieli", 1),
        ("language__pref_label", "saami", 0),
    ],
)
def test_list_datacatalogs_with_filter(
    admin_client, post_datacatalog_payloads_a_b_c, catalog_filter, filter_value, filter_result
):
    url = "/v3/data-catalogs?{0}={1}".format(catalog_filter, filter_value)
    response = admin_client.get(url)
    assert response.status_code == 200
    assert response.data.get("count") == filter_result


def test_list_datacatalogs_with_ordering(admin_client, post_datacatalog_payloads_a_b_c):
    url = "/v3/data-catalogs?ordering=created"
    response = admin_client.get(url)
    results = response.data.get("results")
    assert response.status_code == 200
    assert results[0].get("id") == "urn:nbn:fi:att:data-catalog-testi"
    url = "/v3/data-catalogs?ordering=-created"
    response = admin_client.get(url)
    results = response.data.get("results")
    assert response.status_code == 200
    assert results[0].get("id") == "urn:nbn:fi:att:data-catalog-uusitesti"


def test_get_datacatalog_by_id(admin_client, post_datacatalog_payloads_a_b_c):
    response = admin_client.get("/v3/data-catalogs/urn:nbn:fi:att:data-catalog-uusitesti")
    assert response.status_code == 200
    assert response.data.get("id") == "urn:nbn:fi:att:data-catalog-uusitesti"


def test_delete_datacatalog_by_id(admin_client, post_datacatalog_payloads_a_b_c):
    response = admin_client.delete("/v3/data-catalogs/urn:nbn:fi:att:data-catalog-uusitesti")
    assert response.status_code == 204
    response = admin_client.get("/v3/data-catalogs/urn:nbn:fi:att:data-catalog-uusitesti")
    assert response.status_code == 404


def test_put_datacatalog(admin_client, datacatalog_a_json, data_catalog_list_url):
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res1.status_code == 201

    put_json = {
        "id": res1.data["id"],
        "title": {"en": "Put Catalog"},
        "allowed_pid_types": ["URN", "external"],
    }
    res2 = admin_client.put(
        reverse("datacatalog-detail", kwargs={"pk": res1.data["id"]}),
        put_json,
        content_type="application/json",
    )
    assert res2.status_code == 200

    # values not in put_json should be cleared to defaults
    put_json["allow_remote_resources"] = True  # default is true
    put_json["publishing_channels"] = ["etsin", "ttv"]  # default channels
    assert put_json == {key: value for key, value in res2.json().items() if value}


def test_patch_datacatalog(admin_client, datacatalog_a_json, data_catalog_list_url):
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res1.status_code == 201

    patch_json = {"title": {"en": "Patch Catalog"}}
    res2 = admin_client.patch(
        reverse("datacatalog-detail", kwargs={"pk": res1.data["id"]}),
        patch_json,
        content_type="application/json",
    )
    assert res2.status_code == 200

    # fields in patch_json should replace original values, others unchanged
    assert res2.json() == {
        **res1.json(),
        **patch_json,
    }


def test_add_publishing_channel_to_datacatalog(
    admin_client, datacatalog_a_json, data_catalog_list_url
):
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res1.status_code == 201

    patch_json = {"publishing_channels": ["etsin"]}
    res2 = admin_client.patch(
        reverse("datacatalog-detail", kwargs={"pk": res1.data["id"]}),
        patch_json,
        content_type="application/json",
    )
    assert res2.status_code == 200

    # fields in patch_json should replace original values, others unchanged
    assert res2.json() == {
        **res1.json(),
        **patch_json,
    }


def test_create_datacatalog_with_multiple_publishing_channels(
    admin_client, datacatalog_a_json, data_catalog_list_url
):
    datacatalog_a_json["publishing_channels"] = ["etsin", "ttv"]
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res1.status_code == 201
    assert res1.json()["publishing_channels"] == ["etsin", "ttv"]


def test_try_invalid_publishing_channel_in_datacatalog(
    admin_client, datacatalog_a_json, data_catalog_list_url
):
    datacatalog_a_json["publishing_channels"] = ["foo"]
    res1 = admin_client.post(
        data_catalog_list_url, datacatalog_a_json, content_type="application/json"
    )
    assert res1.status_code == 400
    assert '"foo" is not a valid choice.' in str(res1.json()["publishing_channels"])


def test_create_soft_deleted_datacatalog_again(
    admin_client, datacatalog_a_json, data_catalog_list_url
):
    res1 = admin_client.post(
        data_catalog_list_url,
        {**datacatalog_a_json, "dataset_groups_create": ["somegroup", "othergroup"]},
        content_type="application/json",
    )
    assert res1.status_code == 201
    _id = res1.data["id"]
    res1 = admin_client.delete(
        f"{reverse('datacatalog-detail', args=[_id])}", content_type="application/json"
    )
    assert res1.status_code == 204

    # Recreate catalog, check that it gets updated values and is no longer removed
    res2 = admin_client.post(
        data_catalog_list_url,
        {
            **datacatalog_a_json,
            "title": {"en": "Recreated catalog"},
            "dataset_groups_create": ["newgroup"],
        },
        content_type="application/json",
    )
    assert res2.status_code == 201
    assert "removed" not in res2.data
    assert res2.data["title"] == {"en": "Recreated catalog"}
    assert res2.data["dataset_groups_create"] == ["newgroup"]
