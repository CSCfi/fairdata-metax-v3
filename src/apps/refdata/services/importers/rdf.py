from django.core.serializers import serialize
from django.db import transaction
from django.db.models import prefetch_related_objects
import logging
from time import sleep, time
import requests

from apps.refdata.services.importers.common import BaseDataImporter

from rdflib import RDF, Graph
from rdflib.namespace import SKOS, Namespace

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
                _logger.info("Fetching data from url " + self.source)
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

    def process_fields(self, graph, concept, obj):
        obj.in_scheme = graph.value(concept, SKOS.inScheme)
        obj.pref_label = {
            literal.language: str(literal)
            for literal in graph.objects(concept, SKOS.prefLabel)
        }

        # consider objects without label deprecated
        if len(obj.pref_label) == 0:
            obj.is_removed = True
        else:
            obj.is_removed = False

    def create_or_update_objects(self, graph, objects_by_url):
        new_object_count = 0
        existing_object_count = 0
        deprecated_object_count = 0

        # create or update objects
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            url = str(concept)
            obj = objects_by_url.get(url)
            is_new = not obj
            if is_new:
                obj = self.model(url=url, is_reference_data=True)
                objects_by_url[url] = obj

            self.process_fields(graph, concept, obj)
            obj.save()

            if is_new:
                new_object_count += 1
            else:
                existing_object_count += 1
            if obj.is_removed:
                deprecated_object_count += 1

        return {
            "new": new_object_count,
            "existing": existing_object_count,
            "deprecated": deprecated_object_count,
        }

    def create_relationships(self, graph, objects_by_url):
        """Create hierarchical relationships between graph objects."""
        prefetch_related_objects(list(objects_by_url.values()), "broader", "narrower")

        # clear any previously existing children
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            url = str(concept)
            obj = objects_by_url.get(url)
            if obj.narrower.count() > 0:
                obj.narrower.clear()

        # set parent relations, which will also assign parents' children
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            url = str(concept)
            obj = objects_by_url.get(url)
            parent_urls = [
                str(parent) for parent in graph.objects(concept, SKOS.broader)
            ]
            broader = [
                objects_by_url[parent_url]
                for parent_url in parent_urls
                if parent_url in objects_by_url
            ]
            if len(broader) > 0 or obj.broader.count() > 0:
                obj.broader.set(broader)

    @transaction.atomic
    def save(self, graph):
        _logger.info("Extracting relevant data from the parsed data")

        # keep track of existing and new refdata objects by url
        all_reference_objects = self.model.all_objects.filter(is_reference_data=True)
        objects_by_url = {object.url: object for object in all_reference_objects}

        counts = self.create_or_update_objects(graph, objects_by_url)
        self.create_relationships(graph, objects_by_url)
        _logger.info(
            f"Created {counts['new']} new objects, "
            f"updated {counts['existing']} existing objects "
            f"({counts['deprecated']} deprecated)"
        )

    def load(self):
        response = self.fetch()
        graph = self.parse(response)
        if graph:
            self.save(graph)


class FintoImporter(RemoteRDFReferenceDataImporter):
    """Service for retrieving reference data from Finto."""


class FintoLocationImporter(FintoImporter):
    """Service for retrieving Location reference data from Finto."""

    # rdflib included WGS namespace doesn't work for Finto because it uses https URLs
    WGS = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

    def process_fields(self, graph, concept, obj):
        """Process fieds"""
        super().process_fields(graph, concept, obj)

        long = graph.value(concept, self.WGS.long)
        lat = graph.value(concept, self.WGS.lat)
        wkt = ""
        if not (long is None or lat is None):
            wkt = f"POINT({long} {lat})"
        obj.as_wkt = wkt
