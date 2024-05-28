import io

import pytest
import requests

from apps.core.management.commands._v2_client import MigrationV2Client


def paginated_endpoint_cb(request, context):
    items = list(range(123))
    query = request.qs
    limit = int((query["limit"])[0])
    offset = int((query["offset"])[0])
    next_link = None
    if limit + offset < 123:
        next_link = f"https://paginate.me?offset={offset+limit}&limit={limit}"

    context.status_code = 200
    return {"count": len(items), "results": items[offset : offset + limit], "next": next_link}


@pytest.fixture
def v2_client(requests_mock):
    requests_mock.get("https://paginate.me", json=paginated_endpoint_cb)
    stdout = io.StringIO()
    stderr = io.StringIO()
    client = MigrationV2Client({"use_env": True}, stdout, stderr)
    return client


def test_v2_loop_pagination_batch(v2_client, requests_mock):
    response = requests.get("https://paginate.me?offset=0&limit=50")
    results = list(v2_client.loop_pagination(response, batched=True))
    assert results == [list(range(0, 50)), list(range(50, 100)), list(range(100, 123))]


def test_v2_loop_pagination_no_batch(v2_client, requests_mock):
    response = requests.get("https://paginate.me?offset=0&limit=50")
    results = list(v2_client.loop_pagination(response, batched=False))
    assert results == list(range(123))
