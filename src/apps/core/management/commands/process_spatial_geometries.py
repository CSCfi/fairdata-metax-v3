import logging

from django.core.management.base import BaseCommand

from apps.core.helpers import fill_missing_geometry, normalize_spatial_wkts
from apps.core.models.concepts import Spatial

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize WKT data in spatials."
    help = "Normalize WKT data in spatials and fill missing WKT/geolocations from available data."

    def handle(self, *args, **options):
        spatials = Spatial.all_objects.all()
        normalize_spatial_wkts(spatials)
        fill_missing_geometry(spatials)
