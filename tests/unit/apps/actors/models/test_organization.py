import pytest
from django.db import IntegrityError

from apps.actors.factories import OrganizationFactory


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
