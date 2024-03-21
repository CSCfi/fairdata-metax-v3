from django.utils.translation import gettext as _

from apps.common.serializers.serializers import CommonModelSerializer


class BaseRefdataSerializer(CommonModelSerializer):
    omit_related = False

    def get_fields(self):
        fields = super().get_fields()
        if self.omit_related:
            fields = {
                name: field
                for name, field in fields.items()
                if name not in {"broader", "narrower"}
            }
        return fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if len(rep["pref_label"].keys()) > 4:
            rep["pref_label"] = {
                key: rep["pref_label"][key]
                for key in ["fi", "en", "sv", "und"]
                if key in rep["pref_label"].keys()
            }
        return rep


def get_refdata_serializer_class(refdata_model):
    """Create serializer class for reference data model."""

    class Meta:
        model = refdata_model
        ref_name = getattr(
            refdata_model, "serializer_ref_name", f"Reference{refdata_model.__name__}"
        )

        # using reverse here would cause errors due to circular import, so use hardcoded url
        swagger_description = _("Reference data from `{url}`").format(
            url=f"/v3/reference-data/{refdata_model.get_model_url().replace('?', '')}"
        )

        fields = (
            "id",
            "url",
            "in_scheme",
            "pref_label",
            "broader",
            "narrower",
            "deprecated",
            # include fields defined in refdata_class.serializer_extra_fields
            *getattr(refdata_model, "serializer_extra_fields", ()),
        )

    serializer_class = type(
        f"{refdata_model.__name__}ModelSerializer",
        (BaseRefdataSerializer,),
        {"Meta": Meta},
    )
    return serializer_class
