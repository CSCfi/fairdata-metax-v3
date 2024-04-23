import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

import apps.files.factories as file_factories
from apps.core import factories
from apps.core.models import Contract, DataCatalog, Dataset
from apps.core.serializers import DataCatalogModelSerializer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        if settings.ENV == "production":
            logger.warn("This command can only be used in non-production environments")
            return

        language = factories.LanguageFactory()
        data_catalog = factories.DataCatalogFactory(id="urn:nbn:fi:att:data-catalog-test")
        harvested_data_catalog = factories.DataCatalogFactory(
            id="urn:nbn:fi:att:data-catalog-harvested-test", harvested="True"
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
                "valid_until": "2039-12-31T23:59:00Z",
            },
        )

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
