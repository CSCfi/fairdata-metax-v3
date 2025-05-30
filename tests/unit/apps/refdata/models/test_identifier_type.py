import pytest

from apps.refdata.models import IdentifierType


@pytest.mark.django_db
def test_identifier_type_urn(identifier_type_reference_data):
    assert IdentifierType.get_from_identifier(
        "urn:nbn:fi:att:something"
    ) == IdentifierType.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/identifier_type/code/urn"
    )


@pytest.mark.django_db
def test_identifier_type_doi(identifier_type_reference_data):
    assert IdentifierType.get_from_identifier(
        "doi:10.23729/something"
    ) == IdentifierType.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/identifier_type/code/doi"
    )


@pytest.mark.django_db
def test_identifier_type_other(identifier_type_reference_data):
    assert IdentifierType.get_from_identifier("moro:moro") is None
