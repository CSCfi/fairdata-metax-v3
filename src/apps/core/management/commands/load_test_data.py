import logging

from django.core.management.base import BaseCommand

from apps.core import factories
import apps.files.factories as file_factories

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        language = factories.LanguageFactory()
        homepage = factories.CatalogHomePageFactory()

        dataset_publisher = factories.DatasetPublisherFactory(homepages=(homepage,))
        data_catalog = factories.DataCatalogFactory(
            publisher=dataset_publisher, languages=(language,)
        )
        dataset = factories.DatasetFactory(data_catalog=data_catalog)
        logger.info(f"{dataset=}")
        files = file_factories.create_project_with_files(
            file_paths=[
                "/dir/sub1/file1.csv",
                "/dir/a.txt",
                "/rootfile.txt",
            ],
            file_args={"*": {"byte_size": 1024}},
        )
        file_set = factories.FileSetFactory(
            dataset=dataset, file_storage=files["file_storage"], files=files["files"].values()
        )
        logger.info(
            f"Created test objects: {language=}, {homepage=}, {dataset_publisher=}, {data_catalog=}, "
            f"{dataset=}, {files=}, {file_set=}"
        )
        self.stdout.write("test objects created successfully")
