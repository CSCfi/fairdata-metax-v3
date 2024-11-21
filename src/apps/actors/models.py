import logging
import uuid
from typing import Dict

from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.db.models import Model
from django.utils.translation import gettext as _
from simple_history.models import HistoricalRecords

from apps.common.copier import ModelCopier
from apps.common.helpers import omit_empty
from apps.common.models import AbstractBaseModel

logger = logging.getLogger(__name__)


class HomePage(AbstractBaseModel):
    """A homepage of an entity."""

    copier = ModelCopier(
        copied_relations=[],
        parent_relations=["organization", "person"],
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=512, help_text="Link to homepage.")
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}', null=True)

    history = HistoricalRecords()

    def as_v2_data(self) -> dict:
        data = {"identifier": self.url}
        if self.title:
            data["title"] = self.title
        return data


class OrganizationModelCopier(ModelCopier):
    def copy(
        self,
        original: Model,
        new_values: dict = None,
        copied_objects: dict = None,
        parent_copier=None,
    ) -> Model:
        if original.is_reference_data:
            return (
                original  # Reference data organizations should be used as-is instead of copying.
            )
        return super().copy(original, new_values, copied_objects, parent_copier=parent_copier)


class Organization(AbstractBaseModel):
    """
    Base model for Reference Data objects

    Source: skos:Concept
    https://www.w3.org/TR/skos-reference/#concepts
    """

    # Copying a sub-organization in a dataset should also copy its parents
    copier = OrganizationModelCopier(
        copied_relations=["parent", "homepage"],
        parent_relations=["actor_organizations", "projects", "agencies"],
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=64, null=True)
    in_scheme = models.URLField(max_length=255, null=True, blank=True)
    pref_label = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    homepage = models.OneToOneField(
        HomePage,
        blank=True,
        null=True,
        help_text='example: {"title": {"en": "webpage"}, "url": "https://example.com"}',
        on_delete=models.SET_NULL,
    )
    external_identifier = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text=_("External identifier for the organization."),
    )
    email = models.EmailField(max_length=512, blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        related_name="children",
        blank=True,
        on_delete=models.CASCADE,
        null=True,
    )
    is_reference_data = models.BooleanField(default=False)
    deprecated = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("If set, organization is not shown in organization list by default."),
    )

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
                check=~models.Q(url="") | models.Q(is_reference_data=False),
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
                check=~models.Q(code="") | models.Q(is_reference_data=False),
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
                check=(models.Q(in_scheme__isnull=False) & ~models.Q(in_scheme=""))
                | models.Q(is_reference_data=False),
                name="%(app_label)s_%(class)s_require_reference_data_scheme",
            ),
        ]

    def get_label(self):
        pref_label = self.pref_label or {}
        return pref_label.get("en") or pref_label.get("fi") or next(iter(pref_label.values()), "")

    def as_v2_data(self):
        """Returns v2 organization dictionary"""
        data = {}
        data["@type"] = "Organization"
        data["name"] = self.pref_label
        if identifier := self.url or self.external_identifier:
            data["identifier"] = identifier
        if email := self.email:
            data["email"] = email
        if homepage := self.homepage:
            data["homepage"] = homepage.as_v2_data()
        if parent := self.parent:
            data["is_part_of"] = parent.as_v2_data()
        return omit_empty(data, recurse=True)

    def __str__(self):
        return f"{self.id}: {self.get_label()}"


class Person(AbstractBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copier = ModelCopier(copied_relations=["homepage"], parent_relations=["part_of_actors"])

    name = models.CharField(max_length=512)
    email = models.EmailField(max_length=512, blank=True, null=True)
    external_identifier = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text=_("External identifier for the actor, usually ORCID or similiar"),
    )
    homepage = models.OneToOneField(
        HomePage,
        blank=True,
        null=True,
        help_text='example: {"title": {"en": "webpage"}, "url": "https://example.com"}',
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return str(self.name)


class Actor(AbstractBaseModel):
    """Name of organization or person.

    Different types include e.g. creator, curator, publisher or rights holder.

    Attributes:
        person(Person): Person if any associated with this actor.
        organization(Organization): Organization if any associated with this actor.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        Person, related_name="part_of_actors", null=True, blank=True, on_delete=models.CASCADE
    )
    organization = models.ForeignKey(
        Organization,
        related_name="actor_organizations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def as_v2_data(self) -> Dict:
        """Returns v2 actor dictionary."""
        data = {}
        if self.person:
            data["name"] = self.person.name
            data["@type"] = "Person"
            if identifier := self.person.external_identifier:
                data["identifier"] = identifier
            if self.organization:
                data["member_of"] = self.organization.as_v2_data()
            if homepage := self.person.homepage:
                data["homepage"] = homepage.as_v2_data()
            if email := self.person.email:
                data["email"] = email

        elif self.organization:
            data = self.organization.as_v2_data()
        return data

    def __str__(self):
        if self.person:
            return str(self.person)
        else:
            return str(self.organization)
