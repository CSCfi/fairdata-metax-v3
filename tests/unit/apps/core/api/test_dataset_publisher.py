import datetime
import logging
import pytest

from apps.core.models import DatasetPublisher

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_publisher(client, publisher_a_json):
    res = client.post(
        "/rest/v3/publisher", publisher_a_json, content_type="application/json"
    )
    logger.info(f"{res.data=}")
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_publisher_twice(client, publisher_b_json):
    _now = datetime.datetime.now()
    res1 = client.post(
        "/rest/v3/publisher", publisher_b_json, content_type="application/json"
    )
    assert res1.status_code == 201
    logger.info(f"{res1.data=}")
    res2 = client.post(
        "/rest/v3/publisher", publisher_b_json, content_type="application/json"
    )
    assert res2.status_code == 201
    assert res1.data.get("id") != res2.data.get("id")


@pytest.mark.django_db
def test_create_publisher_error(client, publisher_error_json):
    response = client.post(
        "/rest/v3/publisher", publisher_error_json, content_type="application/json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_publishers(client, post_publisher_payloads_a_b_c_d):
    response = client.get("/rest/v3/publisher")
    logger.info(f"{response.data=}")
    publisher_count = DatasetPublisher.available_objects.all().count()
    assert response.status_code == 200
    assert len(response.data.get("results")) == publisher_count


@pytest.mark.parametrize(
    "publisher_filter, filter_value, filter_result",
    [
        ("name", "sija C", 1),
        ("url", "yyy", 2),
        ("homepage_title", "website", 5),
        ("homepage_title", "C kotisivu", 1),
    ],
)
@pytest.mark.django_db
def test_list_publishers_with_filter(
    client,
    post_publisher_payloads_a_b_c_d,
    publisher_filter,
    filter_value,
    filter_result,
):
    url = "/rest/v3/publisher?{0}={1}".format(publisher_filter, filter_value)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert len(response.data.get("results")) == filter_result


@pytest.mark.django_db
def test_list_publishers_with_page_size(client, post_publisher_payloads_a_b_c_d):
    url = "/rest/v3/publisher?{0}={1}".format("page_size", 2)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert response.data.get("next") is not None


@pytest.mark.django_db
def test_change_publisher(client, publisher_c_json, publisher_put_c_json):
    _now = datetime.datetime.now()
    res1 = client.post(
        "/rest/v3/publisher", publisher_c_json, content_type="application/json"
    )
    publisher_created = DatasetPublisher.objects.get(id=res1.data.get("id"))
    assert publisher_created.name["en"] == "Publisher C"
    response = client.put(
        "/rest/v3/publisher/{id}".format(id=res1.data.get("id")),
        publisher_put_c_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert res1.data.get("id") == response.data.get("id")
    logger.info(str(response.data))
    publisher_changed = DatasetPublisher.objects.get(id=res1.data.get("id"))
    assert publisher_changed.name["en"] == "Publisher C with new page"
    homepages = publisher_changed.homepage.all()
    assert homepages[0].url == "http://uusi.c.publisher.xyz/"
    assert homepages[0].title["en"] == "Publisher new C website"


@pytest.mark.django_db
def test_get_publisher_by_id(client, post_publisher_payloads_a_b_c_d):
    response = client.get("/rest/v3/publisher")
    results = response.data.get("results")
    for result in results:
        publisher_by_id = client.get(
            "/rest/v3/publisher/{id}".format(id=result.get("id"))
        )
        assert response.status_code == 200
        assert publisher_by_id.data.get("name") == result.get("name")


@pytest.mark.django_db
def test_delete_publisher_by_id(client, post_publisher_payloads_a_b_c_d):
    response = client.get("/rest/v3/publisher")
    publisher_count = DatasetPublisher.available_objects.all().count()
    assert response.data.get("count") == publisher_count
    results = response.data.get("results")
    delete_result = client.delete(
        "/rest/v3/publisher/{id}".format(id=results[0].get("id"))
    )
    assert delete_result.status_code == 204
    assert publisher_count - 1 == DatasetPublisher.available_objects.all().count()


@pytest.mark.django_db
def test_list_publishers_with_simple_ordering(client, post_publisher_payloads_a_b_c_d):
    url = "/rest/v3/publisher?ordering=created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("name").get("en") == "Publisher A"

    url = "/rest/v3/publisher?ordering=-created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("name").get("en") == "Publisher D"


@pytest.mark.django_db
def test_list_publishers_with_complex_ordering(client, post_publisher_payloads_a_b_c_d):
    url = "/rest/v3/publisher?ordering=url,created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("name").get("en") == "Publisher D"

    url = "/rest/v3/publisher?ordering=-url,created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("name").get("en") == "Publisher C"
