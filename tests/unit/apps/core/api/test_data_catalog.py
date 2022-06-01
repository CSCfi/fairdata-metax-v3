import datetime
import logging
import pytest

from django.urls import reverse

from apps.core.models import DataCatalog
from apps.core.serializers.data_catalog_serializer import DataCatalogModelSerializer


logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_datacatalog(client, datacatalog_a_json):
    res = client.post('/rest/v3/datacatalog/', datacatalog_a_json, content_type='application/json')
    logger.info(str(res.data))
    assert res.status_code == 201

@pytest.mark.django_db
def test_create_minimal_datacatalog(client, datacatalog_d_json):
    res = client.post('/rest/v3/datacatalog/', datacatalog_d_json, content_type='application/json')
    logger.info(str(res.data))
    assert res.status_code == 201

@pytest.mark.django_db
def test_create_datacatalog_twice(client, datacatalog_a_json):
    _now = datetime.datetime.now()
    res1 = client.post('/rest/v3/datacatalog/', datacatalog_a_json, content_type='application/json')
    assert res1.status_code == 201
    res2 = client.post('/rest/v3/datacatalog/', datacatalog_a_json, content_type='application/json')
    assert res2.status_code == 400

@pytest.mark.django_db
def test_change_datacatalog(client, datacatalog_c_json, datacatalog_put_json):
    _now = datetime.datetime.now()
    res1 = client.post('/rest/v3/datacatalog/', datacatalog_c_json, content_type='application/json')
    response = client.put('/rest/v3/datacatalog/urn:nbn:fi:att:data-catalog-uusitesti', datacatalog_put_json, content_type='application/json')
    assert response.status_code == 200
    logger.info(str(response.data))
    assert len(response.data.get('language')) == 2


@pytest.mark.django_db
def test_change_datacatalog_to_minimal(client, datacatalog_a_json, datacatalog_d_json):
    _now = datetime.datetime.now()
    res1 = client.post('/rest/v3/datacatalog/', datacatalog_a_json, content_type='application/json')
    response = client.put('/rest/v3/datacatalog/urn:nbn:fi:att:data-catalog-testi', datacatalog_d_json, content_type='application/json')
    assert response.status_code == 200
    logger.info(str(response.data))
    assert response.data.get('language', None) == []


@pytest.mark.django_db
def test_change_datacatalog_from_minimal(client, datacatalog_a_json, datacatalog_d_json):
    _now = datetime.datetime.now()
    res1 = client.post('/rest/v3/datacatalog/', datacatalog_d_json, content_type='application/json')
    response = client.put('/rest/v3/datacatalog/urn:nbn:fi:att:data-catalog-testi', datacatalog_a_json, content_type='application/json')
    assert response.status_code == 200
    assert response.data.get('language')[0].get('url') == "http://lexvo.org/id/iso639-3/fin"


@pytest.mark.django_db
def test_create_datacatalog_error(client, datacatalog_error_json):
    _now = datetime.datetime.now()
    res = client.post('/rest/v3/datacatalog/', datacatalog_error_json, content_type='application/json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_list_datacatalogs(client, post_datacatalog_payloads_a_b_c):
    response = client.get('/rest/v3/datacatalog/')
    catalogs = DataCatalog.available_objects.all()
    expected_data = DataCatalogModelSerializer(catalogs, many=True).data
    logger.info(str(response.data.get('results')))
    logger.info(str(expected_data))
    assert response.status_code == 200
    assert response.data.get('count') == 3
    for catalog in response.data.get('results'):
        assert catalog in expected_data


@pytest.mark.parametrize("catalog_filter, filter_value, filter_result", [
    ("harvested", True, 1),
    ("research_dataset_schema", 'att', 3),
    ("dataset_versioning_enabled", True, 1),
    ("dataset_versioning_enabled", False, 2),
    ("title", "katalogi", 3),
    ("title", "New", 1),
    ("id", "nbn:fi:att", 3),
    ("access_rights_description", "repo", 2),
    ("access_type_url", "fairdata", 3),
    ("access_type_title", "open", 2),
    ("publisher_name", "testi", 3),
    ("publisher_homepage_url", ".fi", 3),
    ("publisher_homepage_title", "website", 3),
    ("language_url", "lexvo.org", 3),
    ("language_title", "viro", 1),
    ("language_title", "saami", 0)
])
@pytest.mark.django_db
def test_list_datacatalogs_with_filter(client,
                           post_datacatalog_payloads_a_b_c,
                           catalog_filter,
                           filter_value,
                           filter_result):
    url = '/rest/v3/datacatalog?{0}={1}'.format(catalog_filter, filter_value)
    response = client.get(url)
    assert response.status_code == 200
    assert response.data.get('count') == filter_result


@pytest.mark.django_db
def test_list_datacatalogs_with_ordreing(client,
                           post_datacatalog_payloads_a_b_c):
    url = '/rest/v3/datacatalog?ordering=created:asc'
    response = client.get(url)
    results = response.data.get('results')
    assert response.status_code == 200
    assert results[0].get('id') == 'urn:nbn:fi:att:data-catalog-testi'
    url = '/rest/v3/datacatalog?ordering=created:desc'
    response = client.get(url)
    results = response.data.get('results')
    assert response.status_code == 200
    assert results[0].get('id') == 'urn:nbn:fi:att:data-catalog-uusitesti'


@pytest.mark.django_db
def test_get_datacatalog_by_id(client,
                           post_datacatalog_payloads_a_b_c):
    response = client.get('/rest/v3/datacatalog/urn:nbn:fi:att:data-catalog-uusitesti')
    assert response.status_code == 200
    assert response.data.get('id') == "urn:nbn:fi:att:data-catalog-uusitesti"


@pytest.mark.django_db
def test_delete_datacatalog_by_id(client,
                           post_datacatalog_payloads_a_b_c):
    response = client.delete('/rest/v3/datacatalog/urn:nbn:fi:att:data-catalog-uusitesti')
    assert response.status_code == 204
    response = client.get('/rest/v3/datacatalog/urn:nbn:fi:att:data-catalog-uusitesti')
    assert response.status_code == 404
