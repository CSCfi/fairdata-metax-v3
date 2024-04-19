import logging
from datetime import timedelta

import pytest
from django.utils.timezone import now

from apps.common.helpers import datetime_to_date
from apps.core.models.access_rights import AccessTypeChoices
from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.dataset,
    pytest.mark.usefixtures("data_catalog", "reference_data"),
]


@pytest.fixture
def create_dataset(admin_client, end_users, dataset_a_json):
    def _create(access_rights, state=Dataset.StateChoices.PUBLISHED):
        user = end_users[0].user
        dataset_a_json["metadata_owner"] = {
            "user": user.username,
            "organization": "test",
        }
        dataset_a_json["access_rights"] = access_rights
        dataset_a_json["access_rights"]["license"] = [{"url": "http://uri.suomi.fi/codelist/fairdata/license/code/other"}]
        dataset_a_json["state"] = state
        res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
        assert res.status_code == 201
        return res.data
    
    return _create


@pytest.fixture
def open_dataset(create_dataset):
    return create_dataset({"access_type": {"url": AccessTypeChoices.OPEN}})


@pytest.fixture
def draft_dataset(create_dataset):
    return create_dataset(
        {"access_type": {"url": AccessTypeChoices.OPEN}}, state=Dataset.StateChoices.DRAFT
    )


@pytest.fixture
def login_dataset(create_dataset):
    return create_dataset({"access_type": {"url": AccessTypeChoices.LOGIN}})


@pytest.fixture
def restricted_dataset(create_dataset):
    return create_dataset({"access_type": {"url": AccessTypeChoices.RESTRICTED}})


@pytest.fixture
def available_embargo_dataset(create_dataset):
    return create_dataset(
        {"access_type": {"url": AccessTypeChoices.EMBARGO}, "available": datetime_to_date(now())}
    )


@pytest.fixture
def unavailable_embargo_dataset(create_dataset):
    return create_dataset(
        {
            "access_type": {"url": AccessTypeChoices.EMBARGO},
            "available": datetime_to_date(now() + timedelta(days=3)),
        }
    )


def test_open_dataset_allowed_actions_no_actions(admin_client, open_dataset):
    res = admin_client.get(f"/v3/datasets/{open_dataset['id']}", content_type="application/json")
    assert res.status_code == 200
    assert "allowed_actions" not in res.data


def get_dataset_actions(client, dataset, user=None, expected_status=200):
    if user:
        client.force_login(user)
    res = client.get(
        f"/v3/datasets/{dataset['id']}?include_allowed_actions=true",
        content_type="application/json",
    )
    assert res.status_code == expected_status
    return res.data.get("allowed_actions")


def test_open_dataset_allowed_actions_admin(admin_client, open_dataset):
    assert get_dataset_actions(admin_client, open_dataset) == {
        "download": True,
        "update": True,
    }


def test_open_dataset_allowed_actions_creator(client, end_users, open_dataset):
    assert get_dataset_actions(client, open_dataset, user=end_users[0].user) == {
        "download": True,
        "update": True,
    }


def test_open_dataset_allowed_actions_noncreator(client, end_users, open_dataset):
    assert get_dataset_actions(client, open_dataset, user=end_users[1].user) == {
        "download": True,
        "update": False,
    }


def test_open_dataset_allowed_actions_anonymous(client, open_dataset):
    assert get_dataset_actions(client, open_dataset) == {
        "download": True,
        "update": False,
    }


def test_draft_dataset_allowed_actions_admin(admin_client, end_users, draft_dataset):
    assert get_dataset_actions(admin_client, draft_dataset) == {
        "download": True,
        "update": True,
    }


def test_draft_dataset_allowed_actions_creator(client, end_users, draft_dataset):
    assert get_dataset_actions(client, draft_dataset, user=end_users[0].user) == {
        "download": False,
        "update": True,
    }


def test_draft_dataset_allowed_actions_noncreator(client, end_users, draft_dataset):
    assert (
        get_dataset_actions(client, draft_dataset, expected_status=404, user=end_users[1].user)
        is None
    )


def test_draft_dataset_allowed_actions_anonynomus(client, draft_dataset):
    assert get_dataset_actions(client, draft_dataset, expected_status=404) is None


def test_restricted_dataset_allowed_actions_admin(admin_client, restricted_dataset):
    assert get_dataset_actions(admin_client, restricted_dataset) == {
        "download": True,
        "update": True,
    }


def test_restricted_dataset_allowed_actions_creator(client, end_users, restricted_dataset):
    assert get_dataset_actions(client, restricted_dataset, user=end_users[0].user) == {
        "download": False,
        "update": True,
    }


def test_restricted_dataset_allowed_actions_anonymous(client, restricted_dataset):
    assert get_dataset_actions(client, restricted_dataset) == {
        "download": False,
        "update": False,
    }


def test_login_dataset_allowed_actions_creator(client, end_users, login_dataset):
    assert get_dataset_actions(client, login_dataset, user=end_users[0].user) == {
        "download": True,
        "update": True,
    }


def test_login_dataset_allowed_actions_noncreator(client, end_users, login_dataset):
    assert get_dataset_actions(client, login_dataset, user=end_users[2].user) == {
        "download": True,
        "update": False,
    }


def test_login_dataset_allowed_actions_anonymous(client, login_dataset):
    assert get_dataset_actions(client, login_dataset) == {
        "download": False,
        "update": False,
    }


def test_available_embargo_dataset_allowed_actions_creator(
    client, end_users, available_embargo_dataset
):
    assert get_dataset_actions(client, available_embargo_dataset, user=end_users[0].user) == {
        "download": True,
        "update": True,
    }


def test_available_embargo_dataset_allowed_actions_anonymous(client, available_embargo_dataset):
    assert get_dataset_actions(client, available_embargo_dataset) == {
        "download": True,
        "update": False,
    }


def test_unavailable_embargo_dataset_allowed_actions_creator(
    client, end_users, unavailable_embargo_dataset
):
    assert get_dataset_actions(client, unavailable_embargo_dataset, user=end_users[0].user) == {
        "download": False,
        "update": True,
    }


def test_unavailable_embargo_dataset_allowed_actions_anonymous(
    client, unavailable_embargo_dataset
):
    assert get_dataset_actions(client, unavailable_embargo_dataset) == {
        "download": False,
        "update": False,
    }
