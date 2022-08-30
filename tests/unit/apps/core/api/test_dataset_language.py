import datetime
import logging
import pytest

from apps.core.models import DatasetLanguage

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_language(client, dataset_language_fin_json):
    res = client.post(
        "/rest/v3/datasetlanguage", dataset_language_fin_json, content_type="application/json"
    )
    logger.info(f"{res.data=}")
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_language_twice(client, dataset_language_spa_json):
    _now = datetime.datetime.now()
    res1 = client.post(
        "/rest/v3/datasetlanguage", dataset_language_spa_json, content_type="application/json"
    )
    assert res1.status_code == 201
    logger.info(f"{res1.data=}")
    res2 = client.post(
        "/rest/v3/datasetlanguage", dataset_language_spa_json, content_type="application/json"
    )
    assert res2.status_code == 201
    assert res1.data.get('id') == res2.data.get('id')


@pytest.mark.django_db
def test_create_language_error(client, dataset_language_error_json):
    response = client.post(
        "/rest/v3/datasetlanguage", dataset_language_error_json, content_type="application/json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_languages(client, post_dataset_language_payloads):
    response = client.get("/rest/v3/datasetlanguage")
    logger.info(f"{response.data=}")
    language_count = DatasetLanguage.available_objects.all().count()
    assert response.status_code == 200
    assert len(response.data.get("results")) == language_count


@pytest.mark.parametrize(
    "language_filter, filter_value, filter_result",
    [
        ("url", "iso639", 4),
        ("url", "fi", 1),
        ("title", "kieli", 3),
        ("title", "suomi", 1)
        ]
)

@pytest.mark.django_db
def test_list_languages_with_filter(client, post_dataset_language_payloads, language_filter, filter_value, filter_result):
    url = "/rest/v3/datasetlanguage?{0}={1}".format(language_filter, filter_value)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert len(response.data.get('results')) == filter_result


@pytest.mark.django_db
def test_list_languages_with_page_size(client, post_dataset_language_payloads):
    url = "/rest/v3/datasetlanguage?{0}={1}".format("page_size", 2)
    logger.info(url)
    response = client.get(url)
    logger.info(f"{response.data=}")
    assert response.status_code == 200
    assert response.data.get('next') is not None


@pytest.mark.django_db
def test_change_language(client, dataset_language_fin_json, dataset_language_put_fin_json):
    _now = datetime.datetime.now()
    res1 = client.post(
        "/rest/v3/datasetlanguage", dataset_language_fin_json, content_type="application/json"
    )
    language_created = DatasetLanguage.objects.get(id=res1.data.get('id'))
    assert language_created.title['fi'] == "suomi"
    response = client.put(
        "/rest/v3/datasetlanguage/{id}".format(id=res1.data.get('id')),
        dataset_language_put_fin_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert res1.data.get('id') == response.data.get('id')
    logger.info(str(response.data))
    language_changed = DatasetLanguage.objects.get(id=res1.data.get('id'))
    assert language_changed.title['fi'] == "Suomen kieli"


@pytest.mark.django_db
def test_get_language_by_id(client, post_dataset_language_payloads):
    response = client.get("/rest/v3/datasetlanguage")
    results = response.data.get("results")
    for result in results:
        language_by_id = client.get("/rest/v3/datasetlanguage/{id}".format(id=result.get("id")))
        assert response.status_code == 200
        assert language_by_id.data.get('url') == result.get("url")


@pytest.mark.django_db
def test_delete_language_by_id(client, post_dataset_language_payloads):
    response = client.get("/rest/v3/datasetlanguage")
    language_count = DatasetLanguage.available_objects.all().count()
    assert response.data.get("count") == language_count
    results = response.data.get("results")
    delete_result = client.delete("/rest/v3/datasetlanguage/{id}".format(id=results[0].get("id")))
    assert delete_result.status_code == 204
    assert language_count - 1 == DatasetLanguage.available_objects.all().count()


@pytest.mark.django_db
def test_list_languages_with_simple_ordering(client, post_dataset_language_payloads):
    url = "/rest/v3/datasetlanguage?ordering=created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("url") == "http://lexvo.org/id/iso639-3/est"

    url = "/rest/v3/datasetlanguage?ordering=-created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("url") == "http://lexvo.org/id/iso639-3/spa"


@pytest.mark.django_db
def test_list_languages_with_complex_ordering(client, post_dataset_language_payloads):
    url = "/rest/v3/datasetlanguage?ordering=url,created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("title").get("fi") == "Viron kieli"

    url = "/rest/v3/datasetlanguage?ordering=-url,created"
    res = client.get(url)
    assert res.status_code == 200
    results = res.data.get("results")
    assert results[0].get("title").get("fi") == "Ruotsin kieli"
