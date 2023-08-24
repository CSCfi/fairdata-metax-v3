import pytest
from django.db import IntegrityError

from apps.actors.factories import OrganizationFactory
from apps.actors.models import Organization


def test_create_missing_organization_url():
    with pytest.raises(IntegrityError):
        OrganizationFactory.create(url="")


def test_create_duplicate_organization_url():
    OrganizationFactory.create(url="https://example.com/org")
    with pytest.raises(IntegrityError):
        OrganizationFactory.create(url="https://example.com/org")


def test_create_missing_organization_code():
    with pytest.raises(IntegrityError):
        OrganizationFactory.create(code="")


def test_create_duplicate_organization_code():
    OrganizationFactory.create(code="org")
    with pytest.raises(IntegrityError):
        OrganizationFactory.create(code="org")


def test_create_organization_without_scheme():
    with pytest.raises(IntegrityError):
        OrganizationFactory.create(in_scheme="")


@pytest.mark.django_db
def test_get_organization_with_duplicate_get():
    org1 = OrganizationFactory.create(pref_label={"en": "University of Helsinki"}, url=None)
    org2 = OrganizationFactory.create(
        pref_label={"en": "University of Helsinki", "fi": "Helsingin Yliopisto"},
        url=None,
    )
    org3 = Organization.get_instance_from_v2_dictionary(
        {
            "name": {
                "en": "University of Helsinki",
            }
        }
    )
    best = org3.choose_between(org1)
    assert str(org2.id) == str(org3.id)
    assert str(best.id) == str(org2.id)
