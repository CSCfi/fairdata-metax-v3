from rest_framework import serializers
from apps.rems.types import ApplicationBase, ApplicationLicenseData, LicenseType


class ApplicationCountsSerializer(serializers.Serializer):
    """Serializer for REMS application counts."""

    approved = serializers.IntegerField()
    submitted = serializers.IntegerField()  # includes returned
    # drafts are not included since they are not visible for non-applicants


class ApplicationFieldValueSerializer(serializers.Serializer):
    form = serializers.IntegerField()  # form id
    field = serializers.CharField()  # id of field in the form
    value = serializers.CharField()


class ApplicationDataSerializer(serializers.Serializer):
    accept_licenses = serializers.ListField(child=serializers.IntegerField())
    field_values = serializers.ListField(child=ApplicationFieldValueSerializer(), default=list)


class ApplicationLicenseSerializer(serializers.Serializer):
    """Convert ApplicationLicenseData to same shape as licenses in REMS application responses."""

    def get_fields(self):
        return {
            # Fields defined in dict because the field names are not valid Python identifiers
            "license/id": serializers.IntegerField(source="id"),
            "license/type": serializers.ChoiceField(choices=LicenseType.choices, source="type"),
            "license/title": serializers.DictField(source="title"),
            "license/text": serializers.DictField(source="text"),
            "license/link": serializers.DictField(source="link"),
            "is_data_access_terms": serializers.BooleanField(),  # Metax field, not in REMS
        }

    def to_representation(self, instance: ApplicationLicenseData):
        return super().to_representation(instance)


class ApplicationBaseSerializer(serializers.Serializer):
    """Convert ApplicationBase to format similar licenses in REMS application responses."""

    def get_fields(self):
        # Fields defined in dict because the field names are not valid Python identifiers
        return {
            "application/licenses": ApplicationLicenseSerializer(source="licenses", many=True),
            # Forms are mostly in the same shape in applications as elsewhere
            "application/forms": serializers.JSONField(source="forms"),
        }

    def to_representation(self, instance: ApplicationBase):
        rep = super().to_representation(instance)
        if forms := rep.get("application/forms"):
            for form in forms:
                form.pop("archived", None)
                form.pop("enabled", None)
        return rep
