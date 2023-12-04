import logging

from django.core.management.base import BaseCommand

import apps.files.factories as file_factories
from apps.core import factories
from apps.core.models import Contract

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        language = factories.LanguageFactory()
        data_catalog = factories.DataCatalogFactory(id="urn:data-catalog-test")
        dataset = factories.DatasetFactory(data_catalog=data_catalog, title={"en": "Test dataset"})
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
            f"Created or updated test objects:\n {language=}, \n {data_catalog=}, "
            f"\n {dataset=},\n {files=},\n {contract=}"
        )
        self.stdout.write("test objects created successfully")
