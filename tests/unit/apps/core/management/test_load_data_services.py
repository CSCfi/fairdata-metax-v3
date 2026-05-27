from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.core import factories
from apps.core.models import DataService

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]

DAAS_CATALOG_ID = "urn:nbn:fi:att:data-catalog-daas"


@pytest.fixture
def daas_catalog():
    return factories.DataCatalogFactory(
        id=DAAS_CATALOG_ID,
        title={"en": "DAAS", "fi": "DAAS"},
        dataset_versioning_enabled=True,
        allow_remote_resources=True,
        rems_enabled=False,
        storage_services=[],
        allowed_pid_types=["DOI"],
    )


@patch("apps.core.management.commands.load_data_services.json.load")
@patch("builtins.open", create=True)
def test_load_data_services_syncs_create_update_and_delete(
    mock_file, mock_json_load, daas_catalog
):
    mock_json_load.return_value = [
        {
            "id": "LUMI-AIF",
            "pref_label": {"fi": "LUMI-AIF", "en": "LUMI-AIF"},
            "catalog": DAAS_CATALOG_ID,
        },
        {
            "id": "Allas",
            "pref_label": {"fi": "Allas", "en": "Allas"},
            "catalog": DAAS_CATALOG_ID,
        },
    ]

    assert DataService.objects.count() == 0
    call_command("load_data_services")

    assert DataService.objects.count() == 2
    ds = DataService.objects.get(id="LUMI-AIF")
    assert ds.catalog_id == DAAS_CATALOG_ID
    assert ds.pref_label == {"fi": "LUMI-AIF", "en": "LUMI-AIF"}

    # Sync path: update existing entry and remove missing one
    mock_json_load.return_value = [
        {
            "id": "LUMI-AIF",
            "pref_label": {"fi": "LUMI-AIF (updated)", "en": "LUMI-AIF (updated)"},
            "catalog": DAAS_CATALOG_ID,
        }
    ]
    call_command("load_data_services")

    assert DataService.objects.count() == 1
    ds.refresh_from_db()
    assert ds.pref_label == {"fi": "LUMI-AIF (updated)", "en": "LUMI-AIF (updated)"}
    assert not DataService.objects.filter(id="Allas").exists()

    assert mock_file.call_count == 2
    mock_file.assert_called_with(
        "src/apps/core/management/initial_data/data_services.json", "r"
    )

