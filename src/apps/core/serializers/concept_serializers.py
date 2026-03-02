from django.contrib.gis.geos import GEOSGeometry
from drf_yasg import openapi
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.common.serializers.fields import WKTField
from apps.common.serializers.serializers import CommonListSerializer, CommonModelSerializer
from apps.common.serializers.validators import AnyOf
from apps.core.models import Spatial, concepts, GeoLocation
import json
from apps.core.models.concepts import GeoType

class GeoLocationSerializer(GeoFeatureModelSerializer):

    class Meta:
        model = GeoLocation
        geo_field = "geometry"
        fields = (
            "id",
            "geographic_type",
        )

        swagger_schema_fields = {
            "type": openapi.TYPE_OBJECT,
            "title": "GeoLocation",
            "properties": {
                "id": openapi.Schema(
                    title="Geolocation identifier",
                    type=openapi.FORMAT_UUID,
                    description="The unique identifier of the geolocation",
                ),
                "type": openapi.Schema(
                    title="GeoJSON feature",
                    type=openapi.TYPE_STRING,
                    default="Feature",
                ),
                "geometry": openapi.Schema(
                    title="Geometry",
                    type=openapi.TYPE_OBJECT,
                    description="This field handles following fields: POINT, LINESTRING, POLYGON, MULTIPOINT, MULTILINESTRING, MULTIPOLYGON",
                ),
            },
            "required": ["geometry"],
        }
        auto_bbox = True

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if "properties" in ret:
            ret["properties"].pop("geographic_type", None)

        return ret


class SpatialModelSerializer(CommonModelSerializer):
    """Model Serializer for Spatial"""

    reference = concepts.Location.get_serializer_field(required=False, allow_null=True)
    custom_wkt = serializers.ListField(child=WKTField(), required=False, allow_null=True)
    geolocations = GeoLocationSerializer(many=True, required=False, allow_null=True)

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
        try:
            if geolocations := data.pop("geolocations", None):
                _geolocations = geolocations.get("features", [])
                geo_data = []
                for geolocation in _geolocations:
                    geometry_id = geolocation.get("id", None)
                    geom = GEOSGeometry(json.dumps(geolocation.get("geometry")), srid=4326)
                    gtype = GeoType[geolocation.get("geometry").get("type").upper()].value

                    if not geom.valid:
                        raise serializers.ValidationError({"geolocations": geom.valid_reason})
                    geo_data.append({"geographic_type": gtype, "geometry": geom, "id": geometry_id})
                data["geolocations"] = geo_data
        except Exception as e:
            raise serializers.ValidationError({"geolocations": "Invalid geometry format"})
        data = super().to_internal_value(data)
        return data


    def create(self, validated_data):
        geo_data = validated_data.pop("geolocations", [])

        spatial = super(SpatialModelSerializer, self).create(validated_data)

        if geo_data:
            geo_serializer = GeoLocationSerializer(data=geo_data, many=True)
            if geo_serializer.is_valid(raise_exception=True):
                geo_serializer.save(spatial=spatial)

        return spatial


    def update(self, instance, validated_data):
        if geo_data := validated_data.pop("geolocations", None):
            _existing_geolocations = list(instance.geolocations.values_list("id", flat=True))
            _keep_geolocations_ids = []
            for _geolocation in geo_data:
                if data_id := _geolocation.get("id", None):
                    _keep_geolocations_ids.append(data_id)
                    try:
                        _existing_geolocation = GeoLocation.objects.get(id=data_id)
                        _existing_geolocation.geographic_type = (
                            _geolocation.get("geographic_type", _existing_geolocation.geographic_type))
                        _existing_geolocation.geometry = _geolocation.get("geometry", _existing_geolocation.geometry)
                        _existing_geolocation.save()
                    except GeoLocation.DoesNotExist:
                        GeoLocation.objects.create(spatial=instance, **_geolocation)
                else:
                    GeoLocation.objects.create(spatial=instance, **_geolocation)
            if _remove_locations := GeoLocation.objects.filter(spatial__in=_existing_geolocations).exclude(id__in=_keep_geolocations_ids):
                _remove_locations.delete()
        return super(SpatialModelSerializer, self).update(instance, validated_data)