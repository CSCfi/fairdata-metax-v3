import uuid
from django.db import models
from django.contrib.postgres.fields import HStoreField, ArrayField

from rest_framework import serializers

from apps.core.models.abstracts import AbstractBaseModel


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
    same_as = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    is_reference_data = models.BooleanField(default=False)

    class Meta:
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
                fields = ("id", "url", "in_scheme", "pref_label", "broader", "narrower")

        return BaseSerializer

    def __str__(self):
        pref_label = self.pref_label or {}
        return f"<{self.__class__.__name__} {self.id}: {pref_label.get('en')}>"


class FieldOfScience(AbstractConcept):
    class Meta:
        verbose_name = "field of science"
        verbose_name_plural = "fields of science"
        constraints = AbstractConcept.Meta.constraints
