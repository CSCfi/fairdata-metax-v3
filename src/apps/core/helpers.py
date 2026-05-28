import logging
import re
from typing import TYPE_CHECKING, Iterable

import shapely
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from django.db.models import QuerySet, Q

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


@transaction.atomic
def convert_spatials_wkt_to_geolocations(spatials: Iterable["Spatial"], dry_run=False) -> int:
    """Create spatial geolocations from wkt data.

    Does not clear existing geolocations from spatial."""
    from apps.core.models import GeoLocation

    spatials_updated = 0
    geolocations_to_create = []
    for spatial in spatials:
        wkts = spatial.custom_wkt
        if not wkts and spatial.reference and spatial.reference.as_wkt:
            wkts = [spatial.reference.as_wkt]

        if not wkts:
            continue

        try:
            spatial_geolocations = []
            for wkt in wkts:
                geometry = GEOSGeometry(wkt)
                validate_geometry_coordinates(geometry)
                spatial_geolocations.append(GeoLocation(spatial=spatial, geometry=geometry))

            geolocations_to_create.extend(spatial_geolocations)
            spatials_updated += 1
        except Exception as e:
            # Legacy data may contain invalid wkt
            logger.warning(f"Invalid wkt for Spatial id={spatial.id}: {e!r}")

    if not dry_run:
        GeoLocation.objects.bulk_create(geolocations_to_create, batch_size=5000)
    return spatials_updated


@transaction.atomic
def convert_spatials_geolocations_to_wkt(spatials: Iterable["Spatial"], dry_run=False) -> int:
    """Create spatial custom_wkt entries from geolocations.

    Does not clear existing wkt from spatial."""
    from apps.core.models import Spatial

    spatials_updated = 0
    spatials_to_update = []
    for spatial in spatials:
        if geolocations := spatial.geolocations.all():
            spatial.custom_wkt = spatial.custom_wkt or []  # Ensure custom_wkt list exists
            spatial.custom_wkt.extend(location.geometry.wkt for location in geolocations)
            spatials_to_update.append(spatial)
            spatials_updated += 1

    if not dry_run:
        Spatial.objects.bulk_create(
            spatials_to_update,
            batch_size=5000,
            update_conflicts=True,  # Update files that already exist
            unique_fields=["id"],
            update_fields=["custom_wkt"],
        )
    return spatials_updated


@transaction.atomic
def fill_missing_geometry(queryset: QuerySet["Spatial"]):
    queryset = queryset.prefetch_related("geolocations", "reference")

    # custom_wkt to geolocations
    missing_geolocations = queryset.filter(geolocations__isnull=True).filter(
        Q(custom_wkt__len__gt=0) | Q(reference__as_wkt__isnull=False)
    )
    geolocation_created = convert_spatials_wkt_to_geolocations(missing_geolocations)

    # geolocations to custom_wkt
    missing_wkt = (
        queryset.filter(geolocations__isnull=False)
        .exclude(custom_wkt__len__gt=0)
        .order_by()
        .distinct("id")  # Join with non-null geolocations -> possible duplicate spatials
    )
    wkt_created = convert_spatials_geolocations_to_wkt(missing_wkt)

    logger.info(f"Filled missing geometry: {geolocation_created=} {wkt_created=}")
