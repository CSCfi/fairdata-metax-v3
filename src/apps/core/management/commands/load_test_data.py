import logging

from django.core.management.base import BaseCommand
from apps.core import factories

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        language = factories.LanguageFactory()
        homepage = factories.CatalogHomePageFactory()
        dataset_publisher = factories.DatasetPublisherFactory(homepages=(homepage,))
        data_catalog = factories.DataCatalogFactory(
            publisher=dataset_publisher, languages=(language,)
        )
        research_dataset = factories.ResearchDatasetFactory(data_catalog=data_catalog)
        files = factories.FileFactory.create_batch(3)
        distribution = factories.DistributionFactory(
            files=files, dataset=research_dataset
        )
        logger.info(
            f"Created test objects: {language=}, {homepage=}, {dataset_publisher=}, {data_catalog=}, "
            f"{research_dataset=}, {files=}, {distribution=}"
        )
