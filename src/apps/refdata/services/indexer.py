from django.conf import settings
from django.apps import apps

from apps.refdata.services.importers.rdf import FintoImporter, FintoLocationImporter


def index(types=None):
    """Import reference data to db."""
    importers = {
        "Finto": FintoImporter,
        "FintoLocation": FintoLocationImporter,
    }

    if not types:
        types = settings.REFERENCE_DATA_SOURCES.keys()

    # create importer instances based on configuration
    reference_data_sources = {}
    for typ in types:
        conf = settings.REFERENCE_DATA_SOURCES[typ]
        importer = importers[conf["importer"]]
        model = apps.get_model(conf["model"])
        source = conf["source"]
        reference_data_sources[typ] = importer(model=model, source=source)

    for typ in types:
        reference_data_sources[typ].load()
