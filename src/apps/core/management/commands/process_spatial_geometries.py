import logging

from django.core.management.base import BaseCommand

from apps.core.helpers import normalize_spatial_wkts
from apps.core.models.concepts import Spatial

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize WKT data in spatials."

    def handle(self, *args, **options):
        spatials = Spatial.all_objects.all()
        normalize_spatial_wkts(spatials)
