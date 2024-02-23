import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_swagger():
    """Test that Swagger schema is rendered successfully."""
    client = APIClient()
    res = client.get("/v3/swagger/?format=openapi")
    assert res.status_code == 200
