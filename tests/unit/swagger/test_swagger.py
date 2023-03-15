from rest_framework.test import APIClient


def test_swagger():
    """Test that Swagger schema is rendered successfully."""
    client = APIClient()
    res = client.get("/swagger/?format=openapi")
    assert res.status_code == 200
