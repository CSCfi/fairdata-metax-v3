import time

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.core.models import Contract


class LoadPasTestData(TestCase):
    """
    Tests the load_pas_test_data management command.
    """

    @override_settings(ALLOW_LOAD_PAS_TEST_DATA=True)
    def test_loading_pas_data(self):
        """
        Verify that the command correctly creates the PAS contracts when allowed.
        This test covers the "creation" path.
        """
        self.assertEqual(Contract.all_objects.count(), 0)

        # Command requires the name of the <dataset>.json as an argument
        call_command("load_pas_test_data", "demo")

        expected_contract_count = 25
        self.assertEqual(
            Contract.all_objects.count(),
            expected_contract_count,
            "The total number of contracts should match the number defined in the command.",
        )

        try:
            demo_user_2_contract = Contract.objects.get(
                id="urn:uuid:b9ba17f1-67dc-400f-b7d9-1982540210db"
            )
            self.assertEqual(demo_user_2_contract.title, {"und": "Fairdata Demo User 2 agreement"})
            self.assertEqual(demo_user_2_contract.contact.first().name, "fddps_demo_user_2")

        except Contract.DoesNotExist:
            self.fail("Contract for fddps_demo_user_2 was not created with the correct ID.")

    @override_settings(ALLOW_LOAD_PAS_TEST_DATA=False)
    def test_loading_pas_data_is_disallowed(self):
        """
        Verify that the command does nothing if settings.ALLOW_LOAD_PAS_TEST_DATA is False.
        """
        self.assertEqual(Contract.all_objects.count(), 0)

        call_command("load_pas_test_data", "demo")

        self.assertEqual(
            Contract.all_objects.count(),
            0,
            "No contracts should be created when ALLOW_LOAD_PAS_TEST_DATA is False.",
        )

    @override_settings(ALLOW_LOAD_PAS_TEST_DATA=True)
    def test_updating_existing_pas_data(self):
        """
        Verify that the command correctly updates existing data and is idempotent.
        This test covers the "update" path, fixing the coverage issue.
        """
        # First call to create the data.
        call_command("load_pas_test_data", "demo")
        self.assertEqual(Contract.objects.count(), 25, "Initial creation failed.")
        contract_before_update = Contract.objects.get(
            id="urn:uuid:b9ba17f1-67dc-400f-b7d9-1982540210db"
        )
        modified_time_before = contract_before_update.modified

        # Pause briefly to ensure the 'modified' timestamp will be different
        time.sleep(0.01)

        # Second call to update the data.
        call_command("load_pas_test_data", "demo")

        self.assertEqual(
            Contract.objects.count(), 25, "The command should not create duplicate contracts."
        )

        contract_after_update = Contract.objects.get(
            id="urn:uuid:b9ba17f1-67dc-400f-b7d9-1982540210db"
        )
        modified_time_after = contract_after_update.modified

        self.assertGreater(
            modified_time_after,
            modified_time_before,
            "The 'modified' timestamp should be updated on the second run.",
        )
