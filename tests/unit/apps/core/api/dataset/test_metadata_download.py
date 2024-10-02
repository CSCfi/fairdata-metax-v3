import pytest
from elementpath import select
from lxml import etree
from tests.utils.utils import assert_nested_subdict

from apps.core.factories import (
    DatasetFactory,
    DatasetLicenseFactory,
    FileSetFactory,
    FileStorageFactory,
    SpatialFactory,
)
from apps.core.models import Dataset
from apps.files.factories import FileFactory


def ns_select(*args, **kwargs):
    """Elementpath select with added default namespace."""
    return select(*args, **kwargs, namespaces={"": "http://datacite.org/schema/kernel-4"})


@pytest.fixture
def doi_dataset(admin_client, dataset_maximal_json, data_catalog, reference_data):
    dataset_maximal_json["generate_pid_on_publish"] = "DOI"
    res = admin_client.post(f"/v3/datasets", dataset_maximal_json, content_type="application/json")
    assert res.status_code == 201

    # DOI generation not supported yet, create identifier manually
    Dataset.all_objects.filter(id=res.data["id"]).update(persistent_identifier="doi:some_doi")
    res.data["persistent_identifier"] = "doi:some_doi"
    return res.data


def test_dataset_metadata_download_json(
    admin_client, dataset_a_json, dataset_a, reference_data, data_catalog
):
    assert dataset_a.response.status_code == 201
    id = dataset_a.dataset_id
    res = admin_client.get(f"/v3/datasets/{id}/metadata-download?format=json")
    assert res.status_code == 200
    assert_nested_subdict(dataset_a_json, res.data, ignore=["generate_pid_on_publish"])
    assert res.headers.get("Content-Disposition") == f"attachment; filename={id}-metadata.json"


def test_dataset_metadata_download_json_with_versions(
    admin_client, dataset_a_json, dataset_a, reference_data, data_catalog
):
    assert dataset_a.response.status_code == 201
    new_version = admin_client.post(
        f"/v3/datasets/{dataset_a.dataset_id}/new-version",
        dataset_a_json,
        content_type="application/json",
    )
    assert new_version.status_code == 201
    new_id = new_version.data["id"]
    dataset_a_json["title"] = {"en": "new title"}
    dataset_a_json["state"] = "draft"
    update = admin_client.put(
        f"/v3/datasets/{new_id}", dataset_a_json, content_type="application/json"
    )
    assert update.status_code == 200
    res = admin_client.get(f"/v3/datasets/{new_id}/metadata-download?format=json")
    assert res.status_code == 200
    assert_nested_subdict(dataset_a_json, res.data, ignore=["generate_pid_on_publish"])
    assert res.headers.get("Content-Disposition") == f"attachment; filename={new_id}-metadata.json"


def test_dataset_metadata_download_datacite(admin_client, doi_dataset):
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="other_project")
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    FileSetFactory(dataset_id=doi_dataset["id"], storage=ida_storage, files=files)

    id = doi_dataset["id"]
    res = admin_client.get(f"/v3/datasets/{id}/metadata-download?format=datacite")
    assert res.status_code == 200
    assert res.headers.get("Content-Disposition") == f"attachment; filename={id}-metadata.xml"

    root = etree.XML(res.content)

    # Uncomment to save XML file for debugging
    # et = etree.ElementTree(root)
    # et.write("/tmp/datacite.xml", pretty_print=True)

    # persistent_identifier
    assert ns_select(root, "//identifier/concat(@identifierType, ':', text())") == [
        "DOI:https://doi.org/some_doi"
    ]

    # publisher
    assert ns_select(root, "//publisher/text()") == ["Testiorganisaatio"]

    # publication year
    assert ns_select(root, "//publicationYear/text()") == ["2023"]

    # title
    assert ns_select(root, "//title/concat(@xml:lang, ':', text())") == [
        "en:All Fields Test Dataset",
        "fi:Kaikkien kenttien testiaineisto testi",
    ]

    # description
    assert ns_select(root, "//description/concat(@xml:lang, ':', text())") == [
        f'en:{doi_dataset["description"]["en"]}',
        f'fi:{doi_dataset["description"]["fi"]}',
    ]

    # creators
    parts = "creatorName/@nameType, ':', creatorName/text(), '(', affiliation/text(), ')'"
    assert ns_select(root, f"//creator/concat({parts})") == [
        "Personal:Kuvitteellinen Henkilö(test dept.)",
        "Organizational:Testiorganisaatio()",
        "Personal:Another person(Koneen Säätiö)",
    ]

    assert ns_select(root, "//subject/concat(@xml:lang, ':', text())") == [
        # themes
        "en:data systems designers",
        "fi:atk-suunnittelijat",
        "sv:adb-planerare",
        "en:testing",
        "fi:testaus",
        "sv:testning",
        "sme:testen",
        # fields of science
        "en:Computer and information sciences",
        "fi:Tietojenkäsittely ja informaatiotieteet",
        "sv:Data- och informationsvetenskap",
        # keywords (keywords no defined language)
        ":test",
        ":software development",
        ":web-development",
        ":testi",
        ":ohjelmistokehitys",
        ":web-kehitys",
    ]

    # contributors
    parts = [
        "@contributorType",
        "contributorName/@nameType",
        "contributorName/text()",
        "affiliation/text()",
    ]
    assert ns_select(root, f"//contributor/({', '.join(parts)})") == [
        "DataCurator",
        "Personal",
        "Unexisting Entity",
        "Koneen Säätiö",
    ]

    # language (only one allowed)
    assert ns_select(root, "/resource/language/text()") == ["fi"]

    # licenses
    assert ns_select(root, "//rightsList/rights/concat(@xml:lang, ':', text())") == [
        "en:Other",
        "fi:Muu",
        "en:Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "fi:Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
    ]

    # locations
    parts = (
        "geoLocationPlace/text(), ':', "
        "geoLocationPoint/pointLongitude/text(), ',', "
        "geoLocationPoint/pointLatitude/text()"
    )
    assert ns_select(root, f"//geoLocation/concat({parts})") == [
        "Random Address in Helsinki:,",
        "Another Random Address in Espoo:22.0,61.0",
    ]

    # multipolygon should be split into multiple polygons
    espoo_location = ns_select(
        root, '//geoLocation[geoLocationPlace/text()="Another Random Address in Espoo"]'
    )[0]
    assert len(ns_select(espoo_location, "//geoLocationPolygon")) == 2

    # related identifiers
    parts = "@relationType, ':', @relatedIdentifierType, ':', text()"
    assert ns_select(root, f"//relatedIdentifier/concat({parts})") == [
        "IsIdenticalTo:URL:https://www.example.com",
        "Cites:DOI:https://doi.org/something",
    ]

    # dates
    assert ns_select(root, "//date/concat(@dateType, ':', text())") == [
        "Issued:2023-06-28",
        "Other:2023-08-11/2024-08-11",
        "Other:2023-10-10",
        "Other:2023-12-24",
    ]

    # total file size
    assert ns_select(root, "//size/text()") == [
        "3000 bytes",
    ]


def test_dataset_metadata_download_fairdata_datacite(admin_client):
    dataset = DatasetFactory(title={"en": "Test draft"})
    res = admin_client.get(f"/v3/datasets/{dataset.id}/metadata-download?format=fairdata_datacite")
    assert res.status_code == 200
    assert (
        res.headers.get("Content-Disposition") == f"attachment; filename={dataset.id}-metadata.xml"
    )

    root = etree.XML(res.content)

    # Non-DOI persistent_identifier is stored as an <alternateIdentifier>
    assert ns_select(
        root, "//alternateIdentifier/concat(@alternateIdentifierType, ':', text())"
    ) == [f"Metax dataset ID:{dataset.id}"]

    # title
    assert ns_select(root, "//title/concat(@xml:lang, ':', text())") == [
        "en:Test draft",
    ]


def test_dataset_metadata_download_license_custom_url(admin_client):
    dataset = DatasetFactory(title={"en": "Test draft"})
    dataset.access_rights.license.set(
        [DatasetLicenseFactory(description=None, custom_url="https://example.com/license")]
    )
    res = admin_client.get(f"/v3/datasets/{dataset.id}/metadata-download?format=fairdata_datacite")
    assert res.status_code == 200
    assert (
        res.headers.get("Content-Disposition") == f"attachment; filename={dataset.id}-metadata.xml"
    )

    root = etree.XML(res.content)
    assert ns_select(
        root, "//rightsList/rights/concat(@xml:lang, ':', @rightsURI, ':', text())"
    ) == [
        "en:https://example.com/license:Other",
        "fi:https://example.com/license:Muu",
    ]


def test_dataset_metadata_download_invalid_id(admin_client):
    res = admin_client.get(f"/v3/datasets/invalid_id/metadata-download")
    assert res.status_code == 404
    assert res.headers.get("Content-Disposition") == None
    assert res.data == "Dataset not found."


def test_dataset_metadata_download_datacite_empty_fileset(admin_client, doi_dataset):
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="other_project")
    files = []
    FileSetFactory(dataset_id=doi_dataset["id"], storage=ida_storage, files=files)

    id = doi_dataset["id"]
    res = admin_client.get(f"/v3/datasets/{id}/metadata-download?format=datacite")
    assert res.status_code == 200
    assert res.headers.get("Content-Disposition") == f"attachment; filename={id}-metadata.xml"

    root = etree.XML(res.content)
    assert ns_select(root, "//size/text()") == []


def test_dataset_metadata_download_datacite_no_rights(admin_client, doi_dataset):
    Dataset.all_objects.filter(id=doi_dataset["id"]).update(access_rights=None)
    id = doi_dataset["id"]
    res = admin_client.get(f"/v3/datasets/{id}/metadata-download?format=datacite")
    assert res.status_code == 200

    root = etree.XML(res.content)
    assert ns_select(root, "//rights/text()") == []


def test_dataset_metadata_download_datacite_unknown_other_identifier(admin_client, doi_dataset):
    dataset = Dataset.all_objects.get(id=doi_dataset["id"])
    dataset.other_identifiers.update(notation="jeejee")
    id = doi_dataset["id"]
    res = admin_client.get(f"/v3/datasets/{id}/metadata-download?format=datacite")
    assert res.status_code == 200

    # no "Cites" relation because the identifier type is not known
    root = etree.XML(res.content)
    parts = "@relationType, ':', @relatedIdentifierType, ':', text()"
    assert ns_select(root, f"//relatedIdentifier/concat({parts})") == [
        "IsIdenticalTo:URL:jeejee",  # assume URL as default type
        "Cites:DOI:https://doi.org/something",
    ]


def test_dataset_metadata_download_fairdata_datacite_invalid_wkt(admin_client):
    """Datacite XML should skip invalid WKT"""
    dataset = DatasetFactory(title={"en": "Test draft"})
    dataset.spatial.set([SpatialFactory(custom_wkt=["not wkt"])])
    res = admin_client.get(f"/v3/datasets/{dataset.id}/metadata-download?format=fairdata_datacite")
    assert res.status_code == 200
