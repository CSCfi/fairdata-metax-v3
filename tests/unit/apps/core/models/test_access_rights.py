import pytest


def test_create_access_rights_with_licence_and_access_type(
    access_rights_with_license_and_access_type,
):
    assert access_rights_with_license_and_access_type.id is not None


def test_delete_access_rights_with_licence_and_access_type(
    access_rights_with_license_and_access_type,
):
    license = access_rights_with_license_and_access_type.license
    access_type = access_rights_with_license_and_access_type.access_type
    access_rights_with_license_and_access_type.delete()
    assert (
        license.access_rights.filter(
            id=access_rights_with_license_and_access_type.id
        ).count()
        == 0
    )
    assert (
        access_type.access_rights.filter(
            id=access_rights_with_license_and_access_type.id
        ).count()
        == 0
    )
