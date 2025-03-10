import uuid

import inflection
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.models import AbstractBaseModel
from apps.common.serializers.fields import URLReferencedModelField, URLReferencedModelListField

from .serializers import get_refdata_serializer_class


class AbstractConcept(AbstractBaseModel):
    """
    Base model for Reference Data objects

    Source: skos:Concept
    https://www.w3.org/TR/skos-reference/#concepts
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=255)
    in_scheme = models.URLField(max_length=255, default="", blank=True)
    pref_label = HStoreField(help_text=_('example: {"en":"title", "fi":"otsikko"}'))
    broader = models.ManyToManyField(
        "self",
        related_name="narrower",
        symmetrical=False,
        blank=True,
    )
    same_as = ArrayField(models.CharField(max_length=255), default=list, blank=True)  # owl:sameAs
    deprecated = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("If set, entry is not shown in reference data list by default."),
    )

    class Meta:
        indexes = [
            models.Index(fields=["url"]),
        ]
        abstract = True
        get_latest_by = "modified"
        ordering = ["created"]

        constraints = [
            # All concepts should have a URL.
            models.CheckConstraint(
                check=~models.Q(url=""),
                name="%(app_label)s_%(class)s_require_url",
            ),
            # URLs should be unique within reference data.
            models.UniqueConstraint(
                fields=["url"],
                name="%(app_label)s_%(class)s_unique_reference_data_url",
            ),
            # Reference data should have a scheme.
            models.CheckConstraint(
                check=~models.Q(in_scheme=""),
                name="%(app_label)s_%(class)s_require_reference_data_scheme",
            ),
        ]

    @classmethod
    def get_serializer_class(cls):
        return get_refdata_serializer_class(refdata_model=cls)

    def get_label(self):
        pref_label = self.pref_label if isinstance(self.pref_label, dict) else {}
        return pref_label.get("en") or pref_label.get("fi") or next(iter(pref_label.values()), "")

    def __str__(self):
        return f"{self.id}: {self.get_label()}"

    @classmethod
    def get_model_url(cls) -> str:
        return f"{inflection.dasherize(inflection.underscore(cls.__name__))}s"


class FieldOfScience(AbstractConcept):
    # TODO: Add codes (skos:notation)

    @classmethod
    def get_model_url(cls) -> str:
        return "fields-of-science"

    class Meta(AbstractConcept.Meta):
        verbose_name = "field of science"
        verbose_name_plural = "fields of science"


class Language(AbstractConcept):
    pass


class Theme(AbstractConcept):
    pass


class Location(AbstractConcept):
    as_wkt = models.TextField(null=True, blank=True)
    serializer_extra_fields = ("as_wkt",)


class AccessType(AbstractConcept):
    pass


class ContributorRole(AbstractConcept):
    pass


class ContributorType(AbstractConcept):
    pass


class EventOutcome(AbstractConcept):
    pass


class FileFormatVersion(AbstractConcept):
    file_format = models.CharField(max_length=255)
    format_version = models.CharField(max_length=255, default="", blank=True)
    serializer_extra_fields = ("file_format", "format_version")


class FileType(AbstractConcept):
    pass


class FunderType(AbstractConcept):
    pass


class IdentifierType(AbstractConcept):
    @classmethod
    def get_from_identifier(cls, identifier: str):
        if not identifier:
            return None

        if identifier.startswith("doi:"):
            return IdentifierType.objects.get(
                url="http://uri.suomi.fi/codelist/fairdata/identifier_type/code/doi"
            )
        elif identifier.startswith("urn:"):
            return IdentifierType.objects.get(
                url="http://uri.suomi.fi/codelist/fairdata/identifier_type/code/urn"
            )
        return None


class License(AbstractConcept):
    pass


class LifecycleEvent(AbstractConcept):
    pass


class PreservationEvent(AbstractConcept):
    pass


class RelationType(AbstractConcept):
    pass


class ResearchInfra(AbstractConcept):
    pass


class ResourceType(AbstractConcept):
    pass


class RestrictionGrounds(AbstractConcept):
    @classmethod
    def get_model_url(cls) -> str:
        return "restriction-grounds"

    class Meta(AbstractConcept.Meta):
        verbose_name = "restriction grounds"
        verbose_name_plural = "restriction grounds"


class UseCategory(AbstractConcept):
    @classmethod
    def get_model_url(cls) -> str:
        return "use-categories"


reference_data_models = [
    AccessType,
    ContributorRole,
    ContributorType,
    EventOutcome,
    FieldOfScience,
    FileFormatVersion,
    FileType,
    FunderType,
    IdentifierType,
    Theme,
    Language,
    License,
    LifecycleEvent,
    Location,
    PreservationEvent,
    RelationType,
    ResearchInfra,
    ResourceType,
    RestrictionGrounds,
    UseCategory,
]


def not_implemented_function(*args, **kwargs):
    raise NotImplementedError()


class ConceptProxyMixin:
    """Mixin class for Concept-based proxy models for reference data."""

    @classmethod
    def get_serializer_class(cls):
        """Make non-url fields read-only"""
        if serializer_class := getattr(cls, "_serializer_class", None):
            return serializer_class  # Reuse class instead of always creating new

        serializer_class = super(ConceptProxyMixin, cls).get_serializer_class()
        serializer_class.omit_related = True
        serializer_class.Meta.extra_kwargs = {
            field: {"read_only": True} for field in serializer_class.Meta.fields if field != "url"
        }
        # Remove uniqueness validator since we're not creating new reference data
        serializer_class.Meta.extra_kwargs["url"] = {"validators": []}

        serializer_class.Meta.list_serializer_class = URLReferencedModelListField
        serializer_class.save = not_implemented_function
        serializer_class.create = not_implemented_function
        serializer_class.update = not_implemented_function
        cls._serializer_class = serializer_class
        return serializer_class

    @classmethod
    def get_serializer_field(cls, **kwargs):
        """Return serializer relation field for concept instances."""
        serializer = cls.get_serializer_class()()
        return URLReferencedModelField(child=serializer, **kwargs)

    def __str__(self):
        return self.get_label()

    class Meta:
        proxy = True
