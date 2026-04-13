from apps.core.models.concepts import AccessType
import pytest
from rest_framework.exceptions import ValidationError

from apps.core import factories


pytestmark = [pytest.mark.django_db]


def test_create_access_rights_with_license_and_access_type(access_rights):
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


def test_delete_access_rights_with_license_and_access_type(access_rights, license):
    access_rights.license.set([license])
    license = access_rights.license.first()
    access_type = access_rights.access_type
    access_rights.delete()
    assert license.access_rights.filter(id=access_rights.id).count() == 0
    assert access_type.access_rights.filter(id=access_rights.id).count() == 0


def test_convert_access_type(access_type_reference_data):
    access_rights = factories.AccessRightsFactory(
        access_type=AccessType.objects.get(
            url="http://uri.suomi.fi/codelist/fairdata/access_type/code/permit"
        )
    )

    # No match, access_type unchanged
    access_rights.convert_access_type(
        from_url="http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
        to_url="http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted",
    )
    assert (
        access_rights.access_type.url
        == "http://uri.suomi.fi/codelist/fairdata/access_type/code/permit"
    )

    # Match, but invalid target access type
    with pytest.raises(ValidationError) as ec:
        access_rights.convert_access_type(
            from_url="http://uri.suomi.fi/codelist/fairdata/access_type/code/permit",
            to_url="http://uri.suomi.fi/codelist/fairdata/access_type/code/doesnotexist",
        )
    assert "doesnotexist does not exist" in str(ec.value)

    # Match, access_type is changed
    access_rights.convert_access_type(
        from_url="http://uri.suomi.fi/codelist/fairdata/access_type/code/permit",
        to_url="http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted",
    )
    assert (
        access_rights.access_type.url
        == "http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted"
    )

    # Ensure that updated access type was saved
    access_rights.refresh_from_db()
    assert (
        access_rights.access_type.url
        == "http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted"
    )
