import msgspec
import shapely
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Manager
from drf_yasg import openapi
from rest_framework import serializers
from rest_framework_gis.serializers import (
    GeoFeatureModelListSerializer,
    GeoFeatureModelSerializer,
    GeometryField,
)


from apps.common.helpers import (
    InvalidCoordinates,
    split_geometry_long_edges,
    validate_geometry_coordinates,
)
from apps.common.serializers.fields import ListValidChoicesField, WKTField
from apps.common.serializers.serializers import (
    CommonListSerializer,
    CommonNestedModelSerializer,
    LazyableModelSerializer,
    StrictSerializer,
)
from apps.common.serializers.validators import AnyOf, validate_dict
from apps.core.models import GeoLocation, Spatial, concepts

WGS84_SRID = 4326


def get_geos_exception_msg(error: shapely.errors.GEOSException):
    """Convert GEOSException to a nicer format for end users.

    ParseException: Unknown geometry type! -> "Unknown geometry type"
    """
    err_msg = str(error)
    try:
        err_msg = err_msg.split(":")[1].strip(" !")
    except Exception:
        pass
    return err_msg


class GeoJSONField(serializers.JSONField):
    """Serializer for parsing GeoJSON Geometries."""

    def to_internal_value(self, data):
        validate_dict(data)

        json_bytes = msgspec.json.encode(super().to_internal_value(data))

        # GEOSGeometry is overly permissive, so use shapely to
        # first validate the geometry object.
        try:
            shapely.from_geojson(json_bytes)
        except shapely.errors.GEOSException as e:
            raise serializers.ValidationError(get_geos_exception_msg(e))
        geometry = GEOSGeometry(json_bytes)
        try:
            validate_geometry_coordinates(geometry)
        except InvalidCoordinates as e:
            raise serializers.ValidationError(str(e))
        geometry = split_geometry_long_edges(geometry)
        return geometry


class FeatureSerializer(StrictSerializer):
    """Serializer for parsing GEOJSON Feature."""

    type = ListValidChoicesField(choices=["Feature"])
    geometry = GeoJSONField()
    properties = serializers.JSONField(required=False, validators=[validate_dict])


class FeatureCollectionSerializer(StrictSerializer):
    """Serializer for parsing GeoJSON FeatureCollection."""

    type = ListValidChoicesField(choices=["FeatureCollection"])
    features = FeatureSerializer(many=True, min_length=1)


class GeoFeatureCommonListSerializer(GeoFeatureModelListSerializer, CommonListSerializer):
    """CommonListSerializer that outputs features with GeoJSON formatting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feature_collection_serializer = FeatureCollectionSerializer()

    def to_internal_value(self, data):
        """Convert FeatureCollection dict to a list of GeoLocation dicts."""
        converted = self.feature_collection_serializer.to_internal_value(data)
        geolocations = []
        for feature in converted["features"]:
            geolocations.append(
                {"geometry": feature["geometry"], "properties": feature.get("properties")}
            )
        return geolocations

    def to_representation(self, data):
        """Convert of list of GeoLocations to a FeatureCollection dict."""
        if isinstance(data, Manager):
            data = data.all()
        if not data:
            return None
        return super().to_representation(data)

    class Meta:
        swagger_schema_fields = {
            "type": openapi.TYPE_OBJECT,
            "title": "FeatureCollection",
            "properties": {
                "type": openapi.Schema(
                    title="Type",
                    type=openapi.TYPE_STRING,
                    default="FeatureCollection",
                    enum=["FeatureCollection"],  # Only one supported value
                ),
                "features": openapi.Schema(
                    **{"type": openapi.TYPE_OBJECT, "$ref": "#/definitions/GeoLocation"}
                ),
            },
            "required": ["type", "geometry"],
        }


class GeoLocationSerializer(GeoFeatureModelSerializer, LazyableModelSerializer):

    # Which model fields are updated when doing lazy bulk create/update
    lazy_update_model_fields = ["spatial", "geometry_2d", "geometry_3d", "properties"]

    geometry = GeometryField()

    class Meta:
        model = GeoLocation
        geo_field = "geometry"
        fields = ("geometry", "properties")
        list_serializer_class = GeoFeatureCommonListSerializer

        swagger_schema_fields = {
            "type": openapi.TYPE_OBJECT,
            "title": "GeoLocation",
            "properties": {
                "type": openapi.Schema(
                    title="Type",
                    type=openapi.TYPE_STRING,
                    default="Feature",
                    enum=["Feature"],  # Only one supported value
                ),
                "geometry": openapi.Schema(
                    title="Geometry",
                    type=openapi.TYPE_OBJECT,
                    description=(
                        "This field supports the following geometry types: "
                        "Point, MultiPoint, LineString, MultiLineString, "
                        "Polygon, MultiPolygon, GeometryCollection"
                    ),
                ),
                "properties": openapi.Schema(
                    title="Properties",
                    type=openapi.TYPE_OBJECT,
                    description="Additional properties of the feature.",
                ),
            },
            "required": ["type", "geometry"],
        }
        auto_bbox = True

    def get_properties(self, instance, fields) -> dict | None:
        # Use instance.properties as the value of the "properties" object.
        return instance.properties


class SpatialModelSerializer(CommonNestedModelSerializer):
    """Model Serializer for Spatial"""

    reference = concepts.Location.get_serializer_field(required=False, allow_null=True)
    custom_wkt = serializers.ListField(child=WKTField(), required=False, allow_null=True)
    geolocations = GeoLocationSerializer(many=True, lazy=True, required=False, allow_null=True)

    class Meta:
        model = Spatial
        list_serializer_class = CommonListSerializer
        fields = [
            "full_address",
            "geographic_name",
            "altitude_in_meters",
            "reference",
            "custom_wkt",
            "geolocations",
        ]
        validators = [
            AnyOf(
                [
                    "full_address",
                    "geographic_name",
                    "altitude_in_meters",
                    "reference",
                    "custom_wkt",
                    "geolocations",
                ]
            )
        ]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        geolocations = data.get("geolocations")
        wkts = data.get("custom_wkt")

        reference_wkt = "" # Only used when custom_wkt is not set
        if not wkts and data.get("reference") and data["reference"].as_wkt:
            reference_wkt = data["reference"].as_wkt

        if wkts and geolocations:
            # When both wkt and geojson are provided, they should have the same geometry.
            geolocation_geometries = [
                shapely.wkt.loads(location["geometry"].wkt).normalize()
                for location in geolocations
            ]
            wkt_geometries = [shapely.wkt.loads(wkt).normalize() for wkt in wkts]
            for wkt1, wkt2 in zip(geolocation_geometries, wkt_geometries):
                if not wkt1.equals_exact(wkt2, tolerance=1e-7):
                    raise serializers.ValidationError(
                        {
                            "custom_wkt": (
                                "When both custom_wkt and geolocations are specified, "
                                "both should have exactly the same geometry."
                            )
                        }
                    )
        elif wkts and not geolocations:
            geolocations = [{"geometry": GEOSGeometry(wkt)} for wkt in wkts]
        elif reference_wkt and not geolocations:
            geolocations = [{"geometry": GEOSGeometry(reference_wkt)}]
        elif geolocations and not wkts:
            wkts = [location["geometry"].wkt for location in geolocations]

            # Don't fill custom_wkt from reference location wkt
            if len(wkts) == 1 and reference_wkt:
                wkt_geometry = shapely.wkt.loads(wkts[0]).normalize()
                wkt_ref_geometry = shapely.wkt.loads(reference_wkt).normalize()
                if wkt_geometry.equals_exact(wkt_ref_geometry, tolerance=1e-7):
                    wkts = []

        data["geolocations"] = geolocations
        data["custom_wkt"] = wkts

        return data
