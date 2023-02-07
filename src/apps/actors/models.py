import logging
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.postgres.fields import HStoreField
from django.conf import settings

from apps.core.models.abstracts import AbstractBaseModel
from apps.users.models import MetaxUser

logger = logging.getLogger(__name__)


class Organization(AbstractBaseModel):
    """
    Base model for Reference Data objects

    Source: skos:Concept
    https://www.w3.org/TR/skos-reference/#concepts
    """

    @classmethod
    def get_instance_from_v2_dictionary(cls, org_obj):
        """Gets or creates organization for the actor from v2 organization type actor object.

        Args:
            org_obj (): dictionary with organization name in one or many languages.
                Example dictionary could be {"fi":"csc": "en":"csc"}

        Returns:
            Organization: Organization object corresponding to given name dictionary.

        """
        # https://docs.djangoproject.com/en/4.1/ref/contrib/postgres/fields/#values
        # pref_label is HStoreField that serializes into dictionary object.
        # pref_label__values works as normal python dictionary.values()
        # pref_label__values__contains compares if any given value in a list is contained in the pref_label values.
        org, created = cls.objects.get_or_create(
            pref_label__values__contains=list(org_obj["name"].values()),
            defaults={
                "pref_label": org_obj["name"],
                "homepage": org_obj.get("homepage"),
                "url": org_obj.get("identifier"),
                "in_scheme": settings.ORGANIZATION_SCHEME,
            },
        )
        logger.info(f"{org=}, {created=}")
        return org

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=64, null=True)
    in_scheme = models.URLField(max_length=255, null=False, blank=False)
    pref_label = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    homepage = HStoreField(
        blank=True,
        null=True,
        help_text='example: {"title": {"en": "webpage"}, "identifier": "url"}',
    )
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


class Actor(AbstractBaseModel):
    """Name of organization or person. Different types include e.g. creator, curator, publisher or rights holder.

    Attributes:
        user(MetaxUser): Person if any associated with this actor.
        organization(Organization): Organization if any associated with this actor.
    """
    user = models.ForeignKey(
        get_user_model(),
        related_name="actor_users",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    organization = models.ForeignKey(
        Organization,
        related_name="actor_organizations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def as_v2_data(self):
        data = {}
        if self.user:
            data["name"] = self.user.username
            data["@type"] = "Person"
            if self.organization:
                data["member_of"] = {
                    "name": self.organization.pref_label,
                    "@type": "Organization",
                    "identifier": self.organization.url,
                }
        elif self.organization:
            data["@type"] = "Organization"
            data["name"] = self.organization.pref_label
            if homepage := self.organization.homepage:
                homepage["title"] = eval(homepage["title"])
                data["homepage"] = homepage
        return data

    def __str__(self):
        if self.user and self.user.username:
            return self.user.username
        else:
            return str(self.organization)
