import uuid

from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from rest_framework import serializers

from apps.common.models import AbstractBaseModel


class AbstractConcept(AbstractBaseModel):
    """
    Base model for Reference Data objects

    Source: skos:Concept
    https://www.w3.org/TR/skos-reference/#concepts
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=255)
    in_scheme = models.URLField(max_length=255, default="", blank=True)
    pref_label = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    broader = models.ManyToManyField(
        "self",
        related_name="narrower",
        symmetrical=False,
        blank=True,
    )
    same_as = ArrayField(
        models.CharField(max_length=255), default=list, blank=True
    )  # owl:sameAs
    is_reference_data = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["is_reference_data"]),
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
                condition=models.Q(is_reference_data=True),
                name="%(app_label)s_%(class)s_unique_reference_data_url",
            ),
            # Reference data should have a scheme.
            models.CheckConstraint(
                check=~models.Q(in_scheme="") | models.Q(is_reference_data=False),
                name="%(app_label)s_%(class)s_require_reference_data_scheme",
            ),
        ]

    @classmethod
    def get_serializer(cls):
        class BaseSerializer(serializers.ModelSerializer):
            class Meta:
                model = cls

                # ref_name is used as model name in swagger
                ref_name = getattr(cls, "serializer_ref_name", "ConceptModel")

                fields = (
                    "id",
                    "url",
                    "in_scheme",
                    "pref_label",
                    "broader",
                    "narrower",
                    # include fields defined in model.serializer_extra_fields
                    *getattr(cls, "serializer_extra_fields", ()),
                )

        return BaseSerializer

    def get_label(self):
        pref_label = self.pref_label or {}
        return (
            pref_label.get("en")
            or pref_label.get("fi")
            or next(iter(pref_label.values()), "")
        )

    def __str__(self):
        return f"{self.id}: {self.get_label()}"


class FieldOfScience(AbstractConcept):
    # TODO: Add codes (skos:notation)
    class Meta(AbstractConcept.Meta):
        verbose_name = "field of science"
        verbose_name_plural = "fields of science"


class Language(AbstractConcept):
    pass


class Theme(AbstractConcept):
    pass


class Location(AbstractConcept):
    as_wkt = models.TextField(default="", blank=True)
    serializer_extra_fields = ("as_wkt",)
    serializer_ref_name = "LocationModel"


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
    serializer_ref_name = "FileFormatVersionModel"


class FileType(AbstractConcept):
    pass


class FunderType(AbstractConcept):
    pass


class IdentifierType(AbstractConcept):
    pass


class License(AbstractConcept):
    serializer_ref_name = "LicenseModel"


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
    class Meta(AbstractConcept.Meta):
        verbose_name = "restriction grounds"
        verbose_name_plural = "restriction grounds"


class UseCategory(AbstractConcept):
    pass


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
