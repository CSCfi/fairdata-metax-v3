import pytest

from apps.core.models import Preservation

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


BEFORE = ("core", "0006_add_preservation")
AFTER = ("core", "0007_move_preservation")


@pytest.fixture(autouse=True)
def migration_cleanup(migrator):
    # django-test-migrations does not clean up the database automatically
    # between the tests for some reason. Do so here.
    yield
    migrator.reset()


def test_migrate_to_new(migrator):
    state = migrator.apply_initial_migration(BEFORE)
    # TODO: Required due to wemake-services/django-test-migrations#292.
    # Remove once the bug is fixed.
    state.clear_delayed_apps_cache()
    old_apps = state.apps

    DatasetOld = old_apps.get_model("core", "Dataset")
    ContractOld = old_apps.get_model("core", "Contract")
    DataCatalog = old_apps.get_model("core", "DataCatalog")
    MetadataProvider = old_apps.get_model("core", "MetadataProvider")
    MetaxUser = old_apps.get_model("users", "MetaxUser")

    provider = MetadataProvider.objects.create(
        user=MetaxUser.objects.create(username="test-user"),
        organization="test-org",
    )

    def create_test_dataset(i, **kwargs):
        return DatasetOld.objects.create(
            id=i,
            data_catalog=DataCatalog.objects.create(id=f"test-data-catalog-{i}", title={"en": "Test data catalog {i}"}),
            title={"en": f"Test dataset {i}"},
            metadata_owner=provider,
            **kwargs
        )

    # Create three test entries

    # Has preservation state and contract
    create_test_dataset(
        1,
        preservation_state=10,
        contract=ContractOld.objects.create(
            title={"en": "Test contract 1"},
            quota=1024,
            valid_until="2023-10-10 12:00:00Z"
        )
    )
    # Has preservation identifier
    create_test_dataset(
        2,
        preservation_identifier="preservation-identifier"
    )
    # Has no preservation data
    create_test_dataset(3)

    # Perform the migration
    state = migrator.apply_tested_migration(AFTER)
    state.clear_delayed_apps_cache()
    new_apps = state.apps

    DatasetNew = new_apps.get_model("core", "Dataset")
    dataset_a = DatasetNew.objects.get(id=1)
    assert dataset_a.preservation.contract.title["en"] == "Test contract 1"
    assert dataset_a.preservation.state == 10
    assert dataset_a.preservation.description == None  # Default
    assert dataset_a.preservation.reason_description == ""  # Default

    dataset_b = DatasetNew.objects.get(id=2)
    assert dataset_b.preservation.id == "preservation-identifier"
    assert dataset_b.preservation.state == Preservation.PreservationState.NONE

    # Unrelated dataset without preservation data was left untouched
    dataset_c = DatasetNew.objects.get(id=3)
    assert dataset_c.preservation_id is None


def test_migrate_to_old(migrator):
    state = migrator.apply_initial_migration(AFTER)
    state.clear_delayed_apps_cache()
    new_apps = state.apps

    DatasetNew = new_apps.get_model("core", "Dataset")
    ContractNew = new_apps.get_model("core", "Contract")
    PreservationNew = new_apps.get_model("core", "Preservation")
    DataCatalog = new_apps.get_model("core", "DataCatalog")
    MetadataProvider = new_apps.get_model("core", "MetadataProvider")
    MetaxUser = new_apps.get_model("users", "MetaxUser")

    provider = MetadataProvider.objects.create(
        user=MetaxUser.objects.create(username="test-user"),
        organization="test-org",
    )

    def create_test_dataset(i, **kwargs):
        return DatasetNew.objects.create(
            id=i,
            data_catalog=DataCatalog.objects.create(
                id=f"test-data-catalog-{i}", title={"en": "Test data catalog {i}"}
            ),
            title={"en": f"Test dataset {i}"},
            metadata_owner=provider,
            **kwargs
        )

    # Create three test entries
    # Has preservation state and contract
    create_test_dataset(
        1,
        preservation=PreservationNew.objects.create(
            state=10,
            contract=ContractNew.objects.create(
                title={"en": "Test contract 1"},
                quota=1024,
                valid_until="2023-10-10 12:00:00Z"
            )
        )
    )
    # Has preservation identifier
    create_test_dataset(
        2,
        preservation=PreservationNew.objects.create(id="preservation-identifier")
    )
    # Has no preservation data
    create_test_dataset(3)

    # Perform the migration
    state = migrator.apply_tested_migration(BEFORE)
    state.clear_delayed_apps_cache()
    old_apps = state.apps

    DatasetOld = old_apps.get_model("core", "Dataset")
    dataset_a = DatasetOld.objects.get(id=1)
    assert dataset_a.contract.title["en"] == "Test contract 1"
    assert dataset_a.preservation_state == 10

    dataset_b = DatasetOld.objects.get(id=2)
    assert dataset_b.preservation_identifier == "preservation-identifier"
    assert dataset_b.preservation_state == Preservation.PreservationState.NONE

    # Unrelated dataset without preservation data was left untouched
    dataset_c = DatasetOld.objects.get(id=3)
    assert dataset_c.preservation_identifier is None
