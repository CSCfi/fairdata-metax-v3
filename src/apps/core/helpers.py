import logging
import re
from typing import TYPE_CHECKING

import shapely
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.prototypes.io import wkb_w
from django.db import transaction
from django.db.models import QuerySet

from apps.common.helpers import InvalidCoordinates, normalize_wkt, validate_geometry_coordinates

if TYPE_CHECKING:
    from apps.core.models import Spatial

logger = logging.getLogger(__name__)


def get_metax_identifiers_by_pid(identifier, context={}):
    from apps.core.models.catalog_record import Dataset

    pid = clean_pid(identifier)
    if (pid_map := context.get("datasets_by_pid")) is not None:
        return pid_map.get(pid, [])
    return list(
        Dataset.available_objects.filter(
            persistent_identifier=pid, state=Dataset.StateChoices.PUBLISHED
        ).values_list("id", flat=True)
    )


def clean_pid(pid_string):
    doi_replaced = re.sub("^https://doi.org/", "doi:", pid_string)
    urn_removed = re.sub("^http://urn.fi/", "", doi_replaced)
    return urn_removed


@transaction.atomic
def normalize_spatial_wkts(queryset: QuerySet["Spatial"]) -> int:
    from apps.core.models import Spatial

    spatials_to_update = []
    invalid_count = 0
    update_count = 0
    for spatial in queryset.filter(custom_wkt__len__gt=0):
        try:
            new_custom_wkt = [
                normalize_wkt(wkt, validate_coords=True, split_long_edges=True)
                for wkt in spatial.custom_wkt
            ]
            if new_custom_wkt != spatial.custom_wkt:
                spatial.custom_wkt = new_custom_wkt
                spatials_to_update.append(spatial)
                update_count += 1
        except (shapely.GEOSException, InvalidCoordinates):
            invalid_count += 1

    Spatial.objects.bulk_create(
        spatials_to_update,
        batch_size=5000,
        update_conflicts=True,  # Update files that already exist
        unique_fields=["id"],
        update_fields=["custom_wkt"],
    )
    logger.info(f"Normalized wkts: {update_count=} {invalid_count=}")
    return update_count
