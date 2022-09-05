import datetime
import logging
import pytest

from apps.core.models import AccessRight

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_access_right(client, access_right_alfa_json):
    res = client.post(
        "/rest/v3/accessright", access_right_alfa_json, content_type="application/json"
    )
    logger.info(f"{res.data=}")
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_access_right_twice(client, access_right_beta_json):
    res1 = client.post(
        "/rest/v3/accessright", access_right_beta_json, content_type="application/json"
    )
    assert res1.status_code == 201
    logger.info(f"{res1.data=}")
    res2 = client.post(
        "/rest/v3/accessright", access_right_beta_json, content_type="application/json"
    )
    assert res2.status_code == 201
    assert res1.data.get("id") != res2.data.get("id")


@pytest.mark.django_db
def test_create_access_right_error(client, dataset_access_right_error_json):
    response = client.post(
        "/rest/v3/accessright",
        dataset_access_right_error_json,
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_access_rights(client, post_access_rights_payloads):
    response = client.get("/rest/v3/accessright")
    logger.info(f"{response.data=}")
    count = AccessRight.available_objects.all().count()
    assert response.status_code == 200
    assert len(response.data.get("results")) == count


@pytest.mark.parametrize(
    "access_right_filter, filter_value, filter_result",
    [
        ("description", "aineisto", 4),
        ("description", "Alfa", 1),
        ("access_type_url", "bargo", 1),
        ("access_type_url", "suomi.fi", 4),
        ("access_type_title", "avoin", 1),
        ("access_type_title", "rajoitettu", 2),
        ("license_title", "Commons", 4),
        ("license_title", "Yleismaailmallinen", 1),
        ("license_url", "CC-BY", 3),
    ],
)
@pytest.mark.django_db
def test_list_access_rights_with_filter(
    client,
    post_access_rights_payloads,
    access_right_filter,
    filter_value,
    filter_result,
):
    url = "/rest/v3/accessright?{0}={1}".format(access_right_filter, filter_value)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert len(response.data.get("results")) == filter_result


@pytest.mark.django_db
def test_list_access_rights_with_page_size(client, post_access_rights_payloads):
    url = "/rest/v3/accessright?{0}={1}".format("page_size", 2)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert response.data.get("next") is not None


@pytest.mark.django_db
def test_change_access_right(
    client, access_right_alfa_json, access_right_put_alfa_json
):
    res1 = client.post(
        "/rest/v3/accessright", access_right_alfa_json, content_type="application/json"
    )
    access_right_created = AccessRight.objects.get(id=res1.data.get("id"))
    assert (
        access_right_created.description["fi"] == "Sisältää aineistoja Alfa-palvelusta"
    )
    response = client.put(
        "/rest/v3/accessright/{id}".format(id=res1.data.get("id")),
        access_right_put_alfa_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert res1.data.get("id") == response.data.get("id")
    logger.info(str(response.data))
    access_right_changed = AccessRight.objects.get(id=res1.data.get("id"))
    assert (
        access_right_changed.description["fi"]
        == "Sisältää aineistoja MUUTETTU-palvelusta"
    )


@pytest.mark.django_db
def test_get_access_right_by_id(client, post_access_rights_payloads):
    response = client.get("/rest/v3/accessright")
    results = response.data.get("results")
    for result in results:
        access_right_by_id = client.get(
            "/rest/v3/accessright/{id}".format(id=result.get("id"))
        )
        assert response.status_code == 200
        assert access_right_by_id.data.get("url") == result.get("url")


@pytest.mark.django_db
def test_delete_access_right_by_id(client, post_access_rights_payloads):
    response = client.get("/rest/v3/accessright")
    access_rights_count = AccessRight.available_objects.all().count()
    assert response.data.get("count") == access_rights_count
    results = response.data.get("results")
    delete_result = client.delete(
        "/rest/v3/accessright/{id}".format(id=results[0].get("id"))
    )
    assert delete_result.status_code == 204
    assert access_rights_count - 1 == AccessRight.available_objects.all().count()
    assert access_rights_count == AccessRight.all_objects.all().count()


@pytest.mark.django_db
def test_list_access_rights_with_simple_ordering(client, post_access_rights_payloads):
    url = "/rest/v3/accessright?ordering=created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert (
        results[0].get("description").get("en") == "Contains datasets from Alfa service"
    )

    url = "/rest/v3/accessright?ordering=-created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert (
        results[0].get("description").get("en")
        == "Contains datasets from Delta service"
    )


@pytest.mark.django_db
def test_list_access_rights_with_complex_ordering(client, post_access_rights_payloads):
    url = "/rest/v3/accessright?ordering=access_type_url,created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert (
        results[0].get("access_type").get("url")
        == "http://uri.suomi.fi/codelist/fairdata/access_type/code/embargo"
    )

    url = "/rest/v3/accessright?ordering=-access_type_url,created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert (
        results[0].get("access_type").get("url")
        == "http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted"
    )
