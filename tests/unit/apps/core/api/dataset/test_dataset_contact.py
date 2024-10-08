import logging

import pytest
from django.core import mail
from django.test import override_settings

from apps.core import factories
from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]

email_settings = {"METAX_EMAIL_SENDER": "test-sender@fairdata.fi"}


@pytest.fixture
def dataset_with_emails() -> Dataset:
    dataset = factories.DatasetFactory(persistent_identifier="somepid")
    factories.DatasetActorFactory(
        roles=["creator", "contributor"],
        dataset=dataset,
        person=factories.PersonFactory(email="creator-person@example.com"),
    )
    factories.DatasetActorFactory(
        roles=["creator"],
        dataset=dataset,
        person=factories.PersonFactory(email=None),
        organization=factories.OrganizationFactory(
            email=None, parent=factories.OrganizationFactory(email="creator-org@example.com")
        ),
    )
    factories.DatasetActorFactory(
        roles=["creator"],
        dataset=dataset,
        person=None,
        organization=None,
    )
    factories.DatasetActorFactory(
        roles=["publisher"],
        dataset=dataset,
        person=None,
        organization=factories.OrganizationFactory(email="publisher-org@example.com"),
    )
    dataset.publish()
    return dataset


def test_dataset_contact_get_roles(admin_client, dataset_with_emails):
    res = admin_client.get(
        f"/v3/datasets/{dataset_with_emails.id}/contact", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.json() == {
        "creator": True,
        "curator": False,
        "rights_holder": False,
        "contributor": True,
        "publisher": True,
    }


@override_settings(**email_settings)
def test_dataset_contact_creator(admin_client, dataset_with_emails):
    message = {
        "reply_to": "teppo@test.fi",
        "subject": "Teppo Testaa",
        "body": "Viestin body.",
        "role": "creator",
        "service": "etsin",
    }
    res = admin_client.post(
        f"/v3/datasets/{dataset_with_emails.id}/contact", message, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data == {"recipient_count": 2}

    msg = mail.outbox[0]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert msg.subject == "Message from Etsin / Viesti Etsimestä"
    assert message["subject"] in msg.body
    assert message["body"] in msg.body
    assert set(msg.to) == {"creator-person@example.com", "creator-org@example.com"}


@override_settings(**email_settings)
def test_dataset_contact_publisher_admin(admin_client, dataset_with_emails):
    message = {
        "reply_to": "teppo@test.fi",
        "subject": "Teppo Testaa taas",
        "body": "Viesti julkaisijalle.",
        "role": "publisher",
        "service": "etsin",
    }
    res = admin_client.post(
        f"/v3/datasets/{dataset_with_emails.id}/contact", message, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data == {"recipient_count": 1}

    msg = mail.outbox[0]
    assert set(msg.to) == {"publisher-org@example.com"}


@override_settings(**email_settings)
def test_dataset_contact_publisher_user(user_client, dataset_with_emails):
    message = {
        "reply_to": "seppo@test.fi",
        "subject": "Seppo Testaa taas",
        "body": "Viesti julkaisijalle.",
        "role": "publisher",
        "service": "etsin",
    }
    res = user_client.post(
        f"/v3/datasets/{dataset_with_emails.id}/contact", message, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data == {"recipient_count": 1}

    msg = mail.outbox[0]
    assert set(msg.to) == {"publisher-org@example.com"}


@override_settings(**email_settings)
def test_dataset_contact_publisher_service(service_client, dataset_with_emails):
    message = {
        "reply_to": "test@test.fi",
        "subject": "Test Testaa taas",
        "body": "Viesti julkaisijalle.",
        "role": "publisher",
        "service": "etsin",
    }
    res = service_client.post(
        f"/v3/datasets/{dataset_with_emails.id}/contact", message, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data == {"recipient_count": 1}

    msg = mail.outbox[0]
    assert set(msg.to) == {"publisher-org@example.com"}


@override_settings(**email_settings)
def test_dataset_contact_curator_no_email(admin_client, dataset_with_emails):
    message = {
        "reply_to": "teppo@test.fi",
        "subject": "Teppo Testaa taas",
        "body": "Viesti julkaisijalle.",
        "role": "curator",
        "service": "etsin",
    }
    res = admin_client.post(
        f"/v3/datasets/{dataset_with_emails.id}/contact", message, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data == {"recipient_count": 0}
    assert len(mail.outbox) == 0
