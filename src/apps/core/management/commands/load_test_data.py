import logging

from django.core.management.base import BaseCommand
from apps.core import factories

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        language_fi = factories.LanguageFactory()
        homepage_fairdata = factories.CatalogHomePageFactory()
        dataset_publisher_csc = factories.DatasetPublisherFactory(
            homepages=(homepage_fairdata,)
        )
        data_catalog = factories.DataCatalogFactory(
            publisher=dataset_publisher_csc, languages=(language_fi,)
        )
        research_dataset = factories.ResearchDatasetFactory(data_catalog=data_catalog)
        files = factories.FileFactory.create_batch(3)
        distribution = factories.DistributionFactory(
            files=files, dataset=research_dataset
        )
