import logging
from time import sleep
import requests

from apps.refdata.services.importers.common import BaseDataImporter

from rdflib import RDF, Graph
from rdflib.namespace import SKOS, OWL, Namespace

_logger = logging.getLogger(__name__)


class RemoteRDFReferenceDataImporter(BaseDataImporter):
    """Generic class for importing reference data from remote url."""

    def fetch(self, sleep_time=1, num_retries=7, exp_backoff_multiplier=1.5):
        error = None
        for _ in range(num_retries):

            if error:
                sleep(sleep_time)  # wait before trying to fetch the data again
                sleep_time *= exp_backoff_multiplier  # exponential backoff

            try:
                _logger.info(f"Fetching data from url {self.source}")
                response = requests.get(self.source)
                response.raise_for_status()
                return response
            except Exception as e:
                _logger.error(e)
                error = e

        _logger.error(f"Failed to fetch data of type {self.data_type}, skipping..")
        return None

    def parse(self, response):
        _logger.info("Parsing data")
        graph = Graph().parse(
            data=response.content,
            format=response.headers.get("content-type").split(";")[0],
        )
        return graph

    def data_item_from_graph_concept(self, graph, concept):
        item = {
            "url": str(concept),
            "in_scheme": graph.value(concept, SKOS.inScheme),
            "pref_label": {
                literal.language: str(literal)
                for literal in graph.objects(concept, SKOS.prefLabel)
            },
            "broader": [str(parent) for parent in graph.objects(concept, SKOS.broader)],
            "same_as": [str(same) for same in graph.objects(concept, OWL.sameAs)],
        }
        # consider items without label deprecated
        item["is_removed"] = len(item["pref_label"]) == 0

        return item

    def get_data(self):
        response = self.fetch()
        graph = self.parse(response)

        data = []
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            data.append(self.data_item_from_graph_concept(graph, concept))
        return data


class FintoImporter(RemoteRDFReferenceDataImporter):
    """Service for retrieving reference data from Finto."""


class FintoLocationImporter(FintoImporter):
    """Service for retrieving Location reference data from Finto."""

    # rdflib included WGS namespace doesn't work for Finto because it uses https URLs
    WGS = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

    def data_item_from_graph_concept(self, graph, concept):
        data_item = super().data_item_from_graph_concept(graph, concept)
        long = graph.value(concept, self.WGS.long)
        lat = graph.value(concept, self.WGS.lat)
        wkt = ""
        if not (long is None or lat is None):
            wkt = f"POINT({long} {lat})"
        data_item["as_wkt"] = wkt
        return data_item
