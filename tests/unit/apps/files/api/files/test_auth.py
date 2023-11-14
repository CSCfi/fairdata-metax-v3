import pytest
from rest_framework.reverse import reverse

pytestmark = [pytest.mark.auth]


def test_file_permissions(
    requests_client,
    live_server,
    ida_service_user,
    end_users,
    update_request_client_auth_token,
    ida_file_json,
):
    user1, user2, user3 = end_users
    endpoint = reverse("file-list")
    url = f"{live_server.url}{endpoint}"
    update_request_client_auth_token(requests_client, ida_service_user.token)

    res1 = requests_client.post(url, json=ida_file_json)
    assert res1.status_code == 201

    res2 = requests_client.get(url)
    assert res2.status_code == 200
    assert res2.json()["count"] == 1

    update_request_client_auth_token(requests_client, user1.token)
    res3 = requests_client.post(url, json=ida_file_json)
    assert res3.status_code == 403

    # files are not public unless in a dataset
    res4 = requests_client.get(url)
    assert res4.status_code == 200
    assert res4.json()["count"] == 0
