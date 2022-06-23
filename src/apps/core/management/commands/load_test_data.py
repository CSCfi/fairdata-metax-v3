import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from apps.core import factories

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        language_fi = factories.LanguageFactory(
            url="http://lexvo.org/id/iso639-3/fin",
            title={"en": "Finnish", "fi": "suomi", "sv": "finska", "und": "suomi"},
        )
        homepage_fairdata = factories.CatalogHomePageFactory(
            url="http://fairdata.fi", title={"en": "fairdata", "fi": "fairdata"}
        )
        dataset_publisher_csc = factories.DatasetPublisherFactory(
            name={"fi": "CSC"},
            homepages=(homepage_fairdata,)
        )
        #dataset_publisher_csc.homepage.add(homepage_fairdata)
        licence_cc_4_0 = factories.DatasetLicenseFactory(
            title={
                "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                "und": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
            },
            url="http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
        )
        access_type_open = factories.AccessTypeFactory(
            title={"en": "Open", "fi": "Avoin", "und": "Avoin"},
            url="http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
        )
        access_rights = factories.AccessRightFactory(
            description={
                "en": "Contains datasets from Repotronic service",
                "fi": "Sisältää aineistoja Repotronic-palvelusta",
            },
            access_type=access_type_open,
            license=licence_cc_4_0,
        )
        data_catalog = factories.DataCatalogFactory(
            title={"en": "Testing catalog", "fi": "Testi katalogi"},
            access_rights=access_rights,
            publisher=dataset_publisher_csc,
        )
        data_catalog.language.add(language_fi)
        logger.info(data_catalog)
