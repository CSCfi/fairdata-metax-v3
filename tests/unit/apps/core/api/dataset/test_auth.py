import pytest
from rest_framework.reverse import reverse

pytestmark = [pytest.mark.dataset, pytest.mark.auth]


def test_creator_and_owner_sees_draft(
    requests_client, dataset_a_json, live_server, reference_data, data_catalog, end_users
):
    user1, user2, user3 = end_users

    endpoint = reverse("dataset-list")
    url = f"{live_server.url}{endpoint}"
    requests_client.headers.update({"Authorization": f"Bearer {user3.token}"})

    dataset_a_json["metadata_owner"] = {
        "user": user3.user.username,
        "organization": "test",
    }
    dataset_a_json["state"] = "draft"

    # auth user can create dataset
    res1 = requests_client.post(url, json=dataset_a_json)
    assert res1.status_code == 201

    # auth user can see the created dataset
    res2 = requests_client.get(url)
    assert res2.status_code == 200
    assert res2.json()["count"] == 1

    # other user should not see unpublished dataset
    requests_client.headers.update({"Authorization": f"Bearer {user2.token}"})
    res3 = requests_client.get(url)
    assert res3.status_code == 200
    assert res3.json()["count"] == 0

    # metadata owner should see the draft dataset
    requests_client.headers.update({"Authorization": f"Bearer {user3.token}"})
    res4 = requests_client.get(url)
    assert res4.status_code == 200
    assert res4.json()["count"] == 1

    # metadata owner can edit the dataset
    detail_url = f"{url}/{res1.json()['id']}"
    res5 = requests_client.patch(detail_url, json={"title": {"en": "published title"}})
    res5 = requests_client.post(detail_url + "/publish")
    assert res5.status_code == 200

    # metadata owner makes new draft
    res6 = requests_client.post(f"{detail_url}/create-draft")
    assert res6.status_code == 201

    # user2 should only see the published version
    requests_client.headers.update({"Authorization": f"Bearer {user2.token}"})
    res7 = requests_client.get(detail_url)
    assert res7.status_code == 200
    assert res7.json()["title"] == {"en": "published title"}
