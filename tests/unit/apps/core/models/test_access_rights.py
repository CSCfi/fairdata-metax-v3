import pytest

from apps.core import factories


def test_create_access_rights_with_license_and_access_type(
    access_rights,
):
    assert access_rights.id is not None


def test_access_rights_with_restriction_grounds():
    restriction_grounds = [
        factories.RestrictionGroundsFactory(
            url="http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research"
        )
    ]
    access_rights = factories.AccessRightsFactory(restriction_grounds=restriction_grounds)
    assert restriction_grounds[0].id is not None
    assert access_rights.id is not None


@pytest.mark.django_db
def test_delete_access_rights_with_license_and_access_type(access_rights, license):
    access_rights.license.set([license])
    license = access_rights.license.first()
    access_type = access_rights.access_type
    access_rights.delete()
    assert license.access_rights.filter(id=access_rights.id).count() == 0
    assert access_type.access_rights.filter(id=access_rights.id).count() == 0
