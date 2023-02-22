import logging

from django.core.management.base import BaseCommand

from apps.core import factories
from apps.files.factories import FileFactory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        language = factories.LanguageFactory()
        homepage = factories.CatalogHomePageFactory()
        dataset_publisher = factories.DatasetPublisherFactory(homepages=(homepage,))
        logger.info(f"{dataset_publisher=}")
        data_catalog = factories.DataCatalogFactory(
            publisher=dataset_publisher, languages=(language,)
        )
        logger.info(f"{data_catalog=}")
        dataset = factories.DatasetFactory(data_catalog=data_catalog)
        logger.info(f"{dataset=}")
        files = FileFactory.create_batch(3)
        distribution = factories.DistributionFactory(files=files, dataset=dataset)
        logger.info(
            f"Created test objects: {language=}, {homepage=}, {dataset_publisher=}, {data_catalog=}, "
            f"{dataset=}, {files=}, {distribution=}"
        )
        self.stdout.write("test objects created successfully")
