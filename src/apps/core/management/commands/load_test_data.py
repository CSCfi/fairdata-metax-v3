import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

import apps.files.factories as file_factories
from apps.core import factories
from apps.core.models import Contract, ContractContact, ContractService, DataCatalog, Dataset
from apps.core.serializers import DataCatalogModelSerializer
from apps.core.signals import sync_contract

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not settings.ALLOW_LOAD_TEST_DATA:
            logger.warn("ALLOW_LOAD_TEST_DATA was False. Not executing the command.")
            return

        language = factories.LanguageFactory()
        data_catalog = factories.DataCatalogFactory(
            id="urn:nbn:fi:att:data-catalog-test", allowed_pid_types=["URN", "DOI"]
        )
        harvested_data_catalog = factories.DataCatalogFactory(
            id="urn:nbn:fi:att:data-catalog-harvested-test", is_external="True"
        )
        dataset = None
        files = None
        if not Dataset.objects.filter(title={"en": "Test dataset"}).exists():
            dataset = factories.DatasetFactory(
                data_catalog=data_catalog, title={"en": "Test dataset"}
            )
            logger.info(f"{dataset=}")

            files = file_factories.create_project_with_files(
                file_paths=[
                    "/dir/sub1/file1.csv",
                    "/dir/a.txt",
                    "/rootfile.txt",
                ],
                file_args={"*": {"size": 1024}},
                storage_service="test",
            )
            file_set = factories.FileSetFactory(
                dataset=dataset, storage=files["storage"], files=files["files"].values()
            )

        # Contract needed by IDA tests
        contract = Contract.objects.get_or_create(
            id="495611c1-22b2-4095-bac6-2bf676242a4f",
            defaults={
                "title": {"en": "Test contract"},
                "quota": 123456789,
                "validity_start_date": "2023-06-15",
                "validity_end_date": "2043-12-31",
                "created": "2021-12-31T12:13:14Z",
                "modified": "2021-12-31T12:13:14Z",
            },
        )

        contract_contact = ContractContact.objects.get_or_create(
            contract=contract[0],
            defaults={"name": "Teppo Testaaja", "email": "teppo@email.fi", "phone": ""},
        )

        contract_service = ContractService.objects.get_or_create(
            contract=contract[0], defaults={"name": "Teppo's contract"}
        )

        sync_contract.send(sender=Contract, instance=contract[0])

        logger.info(
            f"Created or updated test objects:\n {language=}, \n {data_catalog=}, \n {harvested_data_catalog=},"
            f"\n {dataset=},\n {files=},\n {contract=}"
        )

        self.create_data_catalogs()

        self.stdout.write("test objects created successfully")

    def create_data_catalogs(self):
        with open(
            "src/apps/core/management/initial_data/initial_data_catalogs.json", "r"
        ) as catalogs_file:
            catalogs_list = json.load(catalogs_file)
            for catalog_json in catalogs_list:  # pragma: no cover
                if data_catalog := DataCatalog.objects.filter(id=catalog_json["id"]).first():
                    serializer = DataCatalogModelSerializer(data_catalog, data=catalog_json)
                    serializer.is_valid()
                    catalog = serializer.update(
                        data_catalog, validated_data=serializer.validated_data
                    )
                    logger.info(f"Updated data catalog: {catalog}")
                    continue

                serializer = DataCatalogModelSerializer(data=catalog_json)
                valid = serializer.is_valid()
                if valid:
                    catalog = serializer.create(validated_data=serializer.validated_data)
                    logger.info(f"Created data catalog: {catalog}")
                else:
                    logger.error(f"Catalog JSON not valid: {serializer.errors}")

            logger.info(f"Created or updated test data-catalogs")

            self.stdout.write("test catalogs created successfully")
