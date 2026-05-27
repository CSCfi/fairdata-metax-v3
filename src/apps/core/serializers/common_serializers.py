import logging
from urllib.parse import urlparse

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import (
    AbstractDatasetModelSerializer,
    AbstractDatasetPropertyModelSerializer,
    AnyOf,
    CommonListSerializer,
    CommonNestedModelSerializer,
)
from apps.common.serializers.fields import (
    MediaTypeField,
    MultiLanguageField,
    PrivateValue,
    RemoteResourceChecksumField,
)
from apps.common.serializers.serializers import CommonModelSerializer, UpdatingListSerializer
from apps.core.helpers import get_metax_identifiers_by_pid
from apps.core.models import AccessRights, CatalogHomePage, DataService, DatasetPublisher, OtherIdentifier
from apps.core.models.catalog_record import RemoteResource, Temporal
from apps.core.models.concepts import (
    AccessType,
    DatasetLicense,
    FileType,
    IdentifierType,
    License,
    RestrictionGrounds,
    UseCategory,
)

logger = logging.getLogger(__name__)


class CatalogHomePageModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = CatalogHomePage
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields
        list_serializer_class = CommonListSerializer


class DatasetPublisherModelSerializer(CommonNestedModelSerializer):
    homepage = CatalogHomePageModelSerializer(many=True)

    class Meta:
        model = DatasetPublisher
        fields = ("id", "name", "homepage")


class LicenseModelSerializer(CommonModelSerializer):
    """Custom serializer for DatasetLicense that does not require pref_label

    Conforms use case where AccessRights object can be created with only url-field in license

    """

    title = MultiLanguageField(default=None, allow_null=True)
    description = MultiLanguageField(default=None, allow_null=True)
    url = serializers.URLField(default=None, allow_null=True)
    pref_label = MultiLanguageField(read_only=True)
    in_scheme = serializers.URLField(max_length=255, read_only=True)

    class Meta:
        model = DatasetLicense
        fields = [
            "id",
            "custom_url",
            "title",
            "description",
            "url",
            "pref_label",
            "in_scheme",
        ]

        ref_name = "DatasetLicense"
        list_serializer_class = UpdatingListSerializer

    def create(self, validated_data):
        reference: License
        custom_url = validated_data.get("custom_url")
        url = validated_data.pop("url", None)

        if url is None and custom_url is None:
            raise serializers.ValidationError(detail="License needs url or custom_url, got None")

        if url is None:
            url = "http://uri.suomi.fi/codelist/fairdata/license/code/other"

        try:
            reference = License.objects.get(url=url)
        except License.DoesNotExist:
            raise serializers.ValidationError(detail=f"License not found {url}")

        return DatasetLicense.objects.create(**validated_data, reference=reference)

    def update(self, instance, validated_data):
        custom_url = validated_data.get("custom_url")
        url = validated_data.pop("url", instance.reference.url)

        if url is None and custom_url is None:
            raise serializers.ValidationError(detail="License needs url or custom_url, got None")

        if url is None:
            url = "http://uri.suomi.fi/codelist/fairdata/license/code/other"

        if url != instance.reference.url:
            try:
                instance.reference = License.objects.get(url=url)
            except License.DoesNotExist:
                raise serializers.ValidationError(detail=f"License not found {url}")

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        refdata_serializer = License.get_serializer_class()
        refdata_serializer.omit_related = True
        serialized_ref = refdata_serializer(instance.reference).data
        rep = super().to_representation(instance)
        return {**rep, **serialized_ref}


class PrivateMultiLanguageValue(PrivateValue):
    """Value container for non-public multilanguage values."""

    def __str__(self) -> str:
        return "<PrivateMultiLanguageValue>"


class PrivateMultiLanguageField(MultiLanguageField):
    """MultiLanguageField that returns non-JSON-serializable value.

    To allow JSON serialization, replace the object with its .value.
    """

    def to_representation(self, value):
        return PrivateMultiLanguageValue(value)


class AccessRightsModelSerializer(CommonNestedModelSerializer):
    license = LicenseModelSerializer(required=False, many=True)
    access_type = AccessType.get_serializer_field(required=True)
    restriction_grounds = RestrictionGrounds.get_serializer_field(required=False, many=True)
    data_access_reviewer_instructions = PrivateMultiLanguageField(required=False)

    def get_fields(self):
        fields = super().get_fields()
        if not settings.REMS_ENABLED:
            fields.pop("rems_approval_type", None)
        return fields

    class Meta:
        model = AccessRights
        fields = (
            "id",
            "description",
            "license",
            "access_type",
            "restriction_grounds",
            "available",
            "rems_approval_type",
            "data_access_application_instructions",
            "data_access_terms",
            "data_access_reviewer_instructions",
            "show_file_metadata",
        )


class OtherIdentifierListSerializer(serializers.ListSerializer):
    def update(self, instance: list, validated_data):
        # Map the other_identifiers instance objects by their notation value
        notation_mapping = {other_id.notation: other_id for other_id in instance}
        data_mapping = {item["notation"]: item for item in validated_data}
        ret = []

        # Perform creations and updates
        for notation, data in data_mapping.items():
            other_identifiers = notation_mapping.get(notation, None)
            if other_identifiers is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(other_identifiers, data))

        # Perform deletions
        for notation, other_id in notation_mapping.items():
            if notation not in data_mapping:
                other_id.delete()

        return ret


class OtherIdentifierModelSerializer(AbstractDatasetModelSerializer):
    identifier_type = IdentifierType.get_serializer_field(required=False, allow_null=True)
    metax_ids = serializers.SerializerMethodField()

    class Meta:
        model = OtherIdentifier
        fields = ("notation", "identifier_type", "old_notation", "metax_ids")
        list_serializer_class = OtherIdentifierListSerializer

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.identifier_type is None:
            rep.pop("identifier_type", None)

        if instance.old_notation is None:
            rep.pop("old_notation", None)

        return rep

    def get_metax_ids(self, instance):
        return get_metax_identifiers_by_pid(instance.notation, self.context)


class TemporalModelSerializer(AbstractDatasetModelSerializer):
    class Meta:
        model = Temporal
        fields = ("start_date", "end_date", "temporal_coverage")
        list_serializer_class = CommonListSerializer
        validators = [AnyOf(["start_date", "end_date", "temporal_coverage"])]

    def validate(self, attrs):
        if attrs.get("start_date") and attrs.get("end_date"):
            if attrs["start_date"] > attrs["end_date"]:
                raise serializers.ValidationError(
                    {
                        "end_date": _(
                            "Value for end_date='{end_date}' is before start_date='{start_date}'."
                        ).format(**attrs)
                    }
                )
        return super().validate(attrs)


class RemoteResourceSerializer(CommonModelSerializer):
    DAAS_CATALOG_ID = "urn:nbn:fi:att:data-catalog-daas"

    use_category = UseCategory.get_serializer_field()
    file_type = FileType.get_serializer_field(required=False, allow_null=True)
    checksum = RemoteResourceChecksumField(required=False, allow_null=True)
    mediatype = MediaTypeField(required=False, allow_null=True)
    access_url = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=2048, validators=[]
    )
    download_url = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=2048, validators=[]
    )
    byte_size = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        error_messages={
            "invalid": _("File size must be an integer number of bytes."),
            "min_value": _("File size cannot be negative."),
        },
    )
    data_service = serializers.SlugRelatedField(
        slug_field="id",
        queryset=DataService.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = RemoteResource
        fields = [
            "title",
            "description",
            "use_category",
            "access_url",
            "download_url",
            "checksum",
            "file_type",
            "mediatype",
            "byte_size",
            "data_service",
        ]
        list_serializer_class = CommonListSerializer

    def _get_catalog_id(self):
        dataset = self.context.get("dataset")
        if dataset and dataset.data_catalog_id:
            return dataset.data_catalog_id

        request = self.context.get("request")
        request_data = getattr(request, "data", None)
        if isinstance(request_data, dict) and request_data.get("data_catalog"):
            return request_data.get("data_catalog")

        current = self
        while current:
            data = getattr(current, "initial_data", None)
            if isinstance(data, dict) and data.get("data_catalog"):
                return data.get("data_catalog")
            current = getattr(current, "parent", None)
        return None

    def _is_daas_catalog(self) -> bool:
        return self._get_catalog_id() == self.DAAS_CATALOG_ID

    @staticmethod
    def _is_file_url(value: str) -> bool:
        if not isinstance(value, str):
            return False
        parsed = urlparse(value)
        return parsed.scheme == "file" and bool(parsed.path)

    def _validate_url_or_file_path(self, value: str) -> str:
        if value in (None, ""):
            return value

        if self._is_daas_catalog() and isinstance(value, str) and value.startswith("/"):
            raise serializers.ValidationError(
                "Use file URL format for local paths, e.g. file:///home/torvinen/data.csv."
            )

        url_validator = serializers.URLField(max_length=2048)
        try:
            url_validator.run_validation(value)
        except serializers.ValidationError:
            if self._is_daas_catalog() and self._is_file_url(value):
                return value
            raise
        return value

    def validate_access_url(self, value):
        return self._validate_url_or_file_path(value)

    def validate_download_url(self, value):
        return self._validate_url_or_file_path(value)

    def validate_data_service(self, value):
        catalog_id = self._get_catalog_id()
        if value is None:
            return value

        if not catalog_id:
            raise serializers.ValidationError(
                "Cannot assign data_service when dataset data_catalog is not set."
            )

        if value.catalog_id != catalog_id:
            raise serializers.ValidationError(
                f"Data service '{value.id}' is not allowed for catalog {catalog_id}."
            )
        return value

    def validate(self, attrs):
        if self._is_daas_catalog():
            data_service = attrs.get("data_service")
            if data_service is None and not getattr(self.instance, "data_service", None):
                raise serializers.ValidationError(
                    {"data_service": "This field is required for DAAS catalog remote resources."}
                )
        return super().validate(attrs)
