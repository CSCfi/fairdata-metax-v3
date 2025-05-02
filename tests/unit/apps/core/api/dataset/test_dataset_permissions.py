import logging
from urllib.parse import parse_qs

import pytest
from django.conf import settings as django_settings
from django.core import mail
from django.test import override_settings
from tests.utils import matchers

from apps.core import factories

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.dataset,
    pytest.mark.usefixtures("data_catalog", "reference_data", "sso_users"),
]

email_settings = {"METAX_EMAIL_SENDER": "test-sender@fairdata.fi"}


def user_status_callback(request, context):
    username = parse_qs(request.body)["id"][0]
    if username != "test_user2":
        context.status_code = 404
        return "not found"
    context.status_code = 200
    return {
        "id": "test_user2",
        "email": "matti@example.com",
        "locked": False,
        "modified": "2023-12-14T05:57:11Z",
        "name": "Matti Mestaaja",
        "qvain_admin_organizations": [],
        "projects": [],
    }


@pytest.fixture
def sso_users(requests_mock, enable_sso):
    return requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json=user_status_callback,
    )


def test_dataset_permissions_creator(admin_client, dataset_a):
    res = admin_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["creators"] == [matchers.DictContaining({"username": "admin"})]


def test_dataset_permissions_add_editors(admin_client, user, dataset_a, sso_users):
    # User already in Metax
    data = {"username": "test_user"}
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert sso_users.call_count == 0

    # User not in Metax, fetch from SSO
    data = {"username": "test_user2"}
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert sso_users.call_count == 1

    res = admin_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors?pagination=false",
        content_type="application/json",
    )
    assert res.data == [
        {
            "username": "test_user",
            "fairdata_username": "test_user",
            "first_name": "Teppo",
            "last_name": "Testaaja",
            "email": "teppo@example.com",
        },
        {
            "username": "test_user2",
            "fairdata_username": "test_user2",
            "first_name": "Matti",
            "last_name": "Mestaaja",
            "email": "matti@example.com",
        },
    ]


def test_dataset_permissions_add_remove_editor(admin_client, user, dataset_a):
    # Add editor, check that successful
    data = {"username": "test_user"}
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201

    res = admin_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["editors"] == [matchers.DictContaining({"username": "test_user"})]

    # Remove editor, check that successful
    res = admin_client.delete(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors/test_user",
        content_type="application/json",
    )
    assert res.status_code == 204

    res = admin_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors?pagination=false",
        content_type="application/json",
    )
    assert res.data == []


def test_dataset_permissions_add_editor_check_dataset(
    admin_client, user, user_client, dataset_a, requests_mock
):
    # Dataset does not show as owned or shared
    res = user_client.get(
        "/v3/datasets?only_owned_or_shared=true&pagination=false", content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data) == 0

    # Dataset permissions not viewable
    res = user_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions", content_type="application/json"
    )
    assert res.status_code == 403

    res = user_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors", content_type="application/json"
    )
    assert res.status_code == 403

    # Dataset not editable
    res = user_client.patch(
        f"/v3/datasets/{dataset_a.dataset_id}",
        data={"title": {"en": "Teppo edited this"}},
        content_type="application/json",
    )
    assert res.status_code == 403

    # Add editor permission
    data = {"username": "test_user"}
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201

    # Dataset shows as shared
    res = user_client.get(
        "/v3/datasets?only_owned_or_shared=true&pagination=false", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data == [matchers.DictContaining({"id": dataset_a.dataset_id})]

    # Dataset permissions viewable
    res = user_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions", content_type="application/json"
    )
    assert res.status_code == 200

    res = user_client.get(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors", content_type="application/json"
    )
    assert res.status_code == 200

    # Dataset editable
    res = user_client.patch(
        f"/v3/datasets/{dataset_a.dataset_id}",
        data={"title": {"en": "Teppo edited this"}},
        content_type="application/json",
    )
    assert res.status_code == 200


def test_dataset_permissions_for_draft_dataset(admin_client, user, user_client, requests_mock):
    dataset = factories.DatasetFactory()

    # Add editor permission
    data = {"username": "test_user"}
    res = admin_client.post(
        f"/v3/datasets/{dataset.id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201

    # User can see the draft
    res = user_client.get("/v3/datasets?pagination=false", content_type="application/json")
    assert res.status_code == 200
    assert res.data == [matchers.DictContaining({"id": str(dataset.id)})]


def test_dataset_permissions_add_creator_as_editor(admin_client, dataset_a):
    data = {"username": "admin"}
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json() == {"username": matchers.StringContaining("is a creator")}


def test_dataset_permissions_add_editor_twice(admin_client, user, user_client, dataset_a):
    data = {"username": "test_user"}
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201

    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json() == {"username": matchers.StringContaining("is already an editor")}


def test_dataset_permissions_add_nonexistent_editor(admin_client, dataset_a):
    data = {"username": "test_user"}  # User not in Metax or SSO
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json() == {"username": "User with username 'test_user' does not exist"}


@override_settings(**email_settings)
def test_dataset_permissions_add_editor_with_message(admin_client, user, user_client, dataset_a):
    data = {
        "username": "test_user",
        "share_message": {"service": "qvain", "content": "Hello world."},
    }
    res = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/permissions/editors",
        data,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert len(mail.outbox) == 1

    msg = mail.outbox[0]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert (
        msg.subject
        == "You have new editing rights in Fairdata Qvain / Sinulla on uusi muokkausoikeus Qvaimessa"
    )
    assert "Hello world." in msg.body
    assert msg.to == ["teppo@example.com"]
