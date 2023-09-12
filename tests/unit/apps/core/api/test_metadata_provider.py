import datetime
import logging

import pytest

from apps.core.models import MetadataProvider

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_metadata_provider(client, metadata_provider_a_json):
    res = client.post(
        "/v3/metadata-provider", metadata_provider_a_json, content_type="application/json"
    )
    logger.info(f"{res.data=}")
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_metadata_provider_twice(client, metadata_provider_b_json):
    _now = datetime.datetime.now()
    res1 = client.post(
        "/v3/metadata-provider", metadata_provider_b_json, content_type="application/json"
    )
    assert res1.status_code == 201
    logger.info(f"{res1.data=}")
    res2 = client.post(
        "/v3/metadata-provider", metadata_provider_b_json, content_type="application/json"
    )
    assert res2.status_code == 201


@pytest.mark.django_db
def test_create_metadata_provider_error(client, metadata_provider_error_json):
    response = client.post(
        "/v3/metadata-provider", metadata_provider_error_json, content_type="application/json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_metadata_providers(client, post_metadata_provider_payloads_a_b_c_d):
    response = client.get("/v3/metadata-provider")
    logger.info(f"{response.data=}")
    metadata_provider_count = MetadataProvider.available_objects.all().count()
    assert response.status_code == 200
    assert len(response.data.get("results")) == metadata_provider_count


@pytest.mark.parametrize(
    "metadata_provider_filter, filter_value, filter_result",
    [
        ("organization", "organ", 4),
        ("user__first_name", "Etunimi", 0),
        ("organization", "organization-a", 1),
    ],
)
@pytest.mark.django_db
def test_list_metadata_providers_with_filter(
    client,
    post_metadata_provider_payloads_a_b_c_d,
    metadata_provider_filter,
    filter_value,
    filter_result,
):
    url = "/v3/metadata-provider?{0}={1}".format(metadata_provider_filter, filter_value)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert len(response.data.get("results")) == filter_result


@pytest.mark.django_db
def test_list_metadata_providers_with_page_size(client, post_metadata_provider_payloads_a_b_c_d):
    url = "/v3/metadata-provider?{0}={1}".format("page_size", 2)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert response.data.get("next") is not None


@pytest.mark.django_db
def test_change_metadata_provider(client, metadata_provider_c_json, metadata_provider_put_c_json):
    _now = datetime.datetime.now()
    res1 = client.post(
        "/v3/metadata-provider", metadata_provider_c_json, content_type="application/json"
    )
    metadata_provider_created = MetadataProvider.objects.get(id=res1.data.get("id"))
    assert metadata_provider_created.user.username == "metax-user-c"
    response = client.put(
        "/v3/metadata-provider/{id}".format(id=res1.data.get("id")),
        metadata_provider_put_c_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    if user1 := res1.data.get("user"):
        if user2 := response.data.get("user"):
            assert user1["username"] != user2["username"]
    assert res1.data.get("organization") == response.data.get("organization")
    logger.info(str(response.data))
    metadata_provider_changed = MetadataProvider.objects.get(id=res1.data.get("id"))
    assert metadata_provider_changed.user.username == "metax-user-c-new"


@pytest.mark.django_db
def test_get_metadata_provider_by_id(client, post_metadata_provider_payloads_a_b_c_d):
    response = client.get("/v3/metadata-provider")
    results = response.data.get("results")
    for result in results:
        metadata_provider_by_id = client.get(
            "/v3/metadata-provider/{id}".format(id=result.get("id"))
        )
        assert response.status_code == 200
        if user1 := metadata_provider_by_id.get("user"):
            if user2 := result.data.get("user"):
                assert user1["username"] == user2["username"]


@pytest.mark.django_db
def test_delete_metadata_provider_by_id(client, post_metadata_provider_payloads_a_b_c_d):
    response = client.get("/v3/metadata-provider")
    metadata_provider_count = MetadataProvider.available_objects.all().count()
    assert response.data.get("count") == metadata_provider_count
    results = response.data.get("results")
    delete_result = client.delete("/v3/metadata-provider/{id}".format(id=results[0].get("id")))
    assert delete_result.status_code == 204
    assert metadata_provider_count - 1 == MetadataProvider.available_objects.all().count()


@pytest.mark.parametrize(
    "metadata_provider_order, order_result",
    [
        ("created", "organization-a.fi"),
        ("-created", "organization-d.fi"),
        ("organization,created", "organization-a.fi"),
        ("-organization,created", "organization-d.fi"),
    ],
)
@pytest.mark.django_db
def test_list_metadata_providers_with_ordering(
    client, post_metadata_provider_payloads_a_b_c_d, metadata_provider_order, order_result
):
    url = "/v3/metadata-provider?ordering={0}".format(metadata_provider_order)
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("organization") == order_result
