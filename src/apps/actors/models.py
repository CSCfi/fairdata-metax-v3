import uuid
from django.db import models
from django.contrib.postgres.fields import HStoreField

from apps.core.models.abstracts import AbstractBaseModel


class Organization(AbstractBaseModel):
    """
    Base model for Reference Data objects

    Source: skos:Concept
    https://www.w3.org/TR/skos-reference/#concepts
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=255)
    code = models.CharField(max_length=64)
    in_scheme = models.URLField(max_length=255, null=False, blank=False)
    pref_label = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    # TODO: Other identifier field

    parent = models.ForeignKey(
        "self",
        related_name="children",
        blank=True,
        on_delete=models.CASCADE,
        null=True,
    )
    is_reference_data = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["is_reference_data"]),
            models.Index(fields=["url"]),
        ]
        get_latest_by = "modified"
        ordering = ["created"]

        constraints = [
            # Reference organizations should have a URL.
            models.CheckConstraint(
                check=~models.Q(url="")  | models.Q(is_reference_data=False) ,
                name="%(app_label)s_%(class)s_require_url",
            ),
            # Reference organization urls should be unique.
            models.UniqueConstraint(
                fields=["url"],
                condition=models.Q(is_reference_data=True),
                name="%(app_label)s_%(class)s_unique_organization_url",
            ),
            # Reference organizations should have a code.
            models.CheckConstraint(
                check=~models.Q(code="")  | models.Q(is_reference_data=False) ,
                name="%(app_label)s_%(class)s_require_code",
            ),
            # Codes should be unique within reference data.
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(is_reference_data=True),
                name="%(app_label)s_%(class)s_unique_organization_code",
            ),
            # Reference organizations should have a scheme.
            models.CheckConstraint(
                check=~models.Q(in_scheme="") | models.Q(is_reference_data=False),
                name="%(app_label)s_%(class)s_require_reference_data_scheme",
            ),
        ]

    def get_label(self):
        pref_label = self.pref_label or {}
        return (
            pref_label.get("en")
            or pref_label.get("fi")
            or next(iter(pref_label.values()), "")
        )

    def __str__(self):
        return f"<{self.__class__.__name__} {self.id}: {self.get_label()}>"
