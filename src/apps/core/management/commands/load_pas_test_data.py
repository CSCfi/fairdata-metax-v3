import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Contract, ContractContact, ContractService
from apps.core.signals import sync_contract

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Loads or updates demo contracts from a specified JSON file located "
        "in the '.../management/initial_data/' directory."
    )

    def add_arguments(self, parser):
        """
        Adds a required positional argument for the data profile to load.
        """
        parser.add_argument(
            "dataset_name",
            type=str,
            help="The name of the dataset to load (e.g., 'demo'), corresponding "
            "to a 'pas_contracts_{dataset_name}.json' file.",
        )

    def handle(self, *args, **options):
        if not settings.ALLOW_LOAD_PAS_TEST_DATA:
            logger.warning("ALLOW_LOAD_PAS_TEST_DATA was False. Not executing the command.")
            return

        dataset = options["dataset_name"]
        file_name = f"pas_contracts_{dataset}.json"

        # The JSON file is expected to be in `.../management/initial_data/`
        # e.g., .../management/initial_data/pas_contracts_demo.json
        try:
            management_dir = Path(__file__).resolve().parent.parent
            data_dir = management_dir / "initial_data"
            json_file_path = data_dir / file_name

            with open(json_file_path, "r", encoding="utf-8") as f:
                contracts_to_process = json.load(f)
        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(f"Error: Data file not found at '{json_file_path}'")
            )
            return
        except json.JSONDecodeError:
            self.stderr.write(
                self.style.ERROR(f"Error: Could not decode JSON from '{json_file_path}'.")
            )
            return

        created_count = 0
        updated_count = 0

        for contract_data in contracts_to_process:
            was_created = self.create_or_update_contract(contract_data)
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Data processing from '{file_name}' complete. "
                f"Created: {created_count}, "
                f"Updated: {updated_count}, "
                f"Total: {len(contracts_to_process)}"
            )
        )

    def create_or_update_contract(self, data: dict) -> bool:
        """
        Creates or updates a single contract and its related objects.
        Returns True if the contract was created, False if it was updated.
        """
        contract_id_full = data["id"]
        contract_title = data["title"]
        now = timezone.now()

        pas_contract, created = Contract.objects.get_or_create(
            id=contract_id_full,
            defaults={
                "title": {"und": contract_title},
                "quota": 123456789,
                "validity_start_date": "2023-01-01",
                "validity_end_date": "2099-12-31",
                "created": now,
                "modified": now,
            },
        )

        # If the contract already existed, update its fields to match the script
        if not created:
            pas_contract.title = {"und": contract_title}
            pas_contract.modified = now
            pas_contract.save(update_fields=["title", "modified"])

        # CLEANUP: Delete old related objects to ensure a clean state
        ContractContact.objects.filter(contract=pas_contract).delete()
        ContractService.objects.filter(contract=pas_contract).delete()

        # CREATE: Create new, correct related objects
        ContractContact.objects.create(
            contract=pas_contract,
            name=data["contact_name"],
            email="fairdata-test@postit.csc.fi",
            phone="+358-10-12345678",
        )
        ContractService.objects.create(
            contract=pas_contract,
            identifier="urn:nbn:fi:att:file-storage-pas",
            name="Fairdata-PAS",
        )

        # Send the signal to sync the contract
        sync_contract.send(sender=Contract, instance=pas_contract)

        if created:
            logger.info(f"Created new demo contract: {contract_title} ({contract_id_full})")
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created contract: {contract_title}")
            )
        else:
            logger.info(f"Updated existing demo contract: {contract_title} ({contract_id_full})")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Contract '{contract_title}' already existed. Ensured it is up to date."
                )
            )

        return created
