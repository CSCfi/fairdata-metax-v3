import uuid

from django.contrib.auth.models import AbstractUser, AnonymousUser, UserManager
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from apps.common.models import CustomSoftDeletableManager, CustomSoftDeletableModel
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class AdminOrganization(CustomSoftDeletableModel):
    id = models.CharField(
        max_length=255, primary_key=True
    )  # https://refeds.org/specifications/schac
    pref_label = HStoreField(
        help_text=_('example: {"en":"title", "fi":"otsikko"}'), null=True, blank=True
    )
    other_identifier = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    url = models.URLField(max_length=255, blank=True, null=True)

    # Is manual REMS approval supported for the organization?
    allow_manual_rems_approval = models.BooleanField(default=False)

    dac_email = models.EmailField(
        help_text=(
            "If set, REMS application related emails are sent "
            "to this address instead of individual handlers."
        ),
        blank=True,
        null=True,
    )

    # Relations to MetaxUser with related_name="admin_organizations"

    def save(self, *args, **kwargs):
        cache.delete("available_admin_organizations")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        cache.delete("available_admin_organizations")
        return super().delete(*args, **kwargs)

    def count_manual_rems_approval_datasets(self):
        from apps.core.models import Dataset
        from apps.core.models.access_rights import REMSApprovalType

        datasets = Dataset.objects.filter(
            metadata_owner__admin_organization=self.id,
            access_rights__rems_approval_type=REMSApprovalType.MANUAL,
        )
        return datasets.count()

    class Meta:
        verbose_name = "admin organization"
        verbose_name_plural = "admin organizations"
        ordering = ["id"]


class MetaxUserManager(UserManager):
    def get_organization_admins(self, organization: str) -> models.QuerySet:
        """List all admin users of given organization."""
        return self.filter(admin_organizations__contains=[organization])


class SoftDeletableMetaxUserManager(MetaxUserManager, CustomSoftDeletableManager):
    pass


class MetaxUser(AbstractUser, CustomSoftDeletableModel):
    """Basic Metax User."""

    objects = SoftDeletableMetaxUserManager()
    available_objects = SoftDeletableMetaxUserManager()
    all_objects = MetaxUserManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # if True, don't display User details
    is_hidden = models.BooleanField(default=False)
    fairdata_username = models.CharField(max_length=64, blank=True, null=True)
    csc_projects = ArrayField(models.CharField(max_length=256), default=list, blank=True)
    synced = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When user data was synchronized from an external service."),
    )
    organization = models.CharField(max_length=512, blank=True, null=True)
    admin_organizations = ArrayField(models.CharField(max_length=512), default=list, blank=True)
    default_admin_organization = models.ForeignKey(
        AdminOrganization,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="The default admin organization for the user.",
    )

    # Track changes to values in admin_organizations
    tracker = FieldTracker(fields=["admin_organizations"])

    def undelete(self):
        self.removed = None
        self.is_hidden = False
        self.save()

    @cached_property
    def is_v2_migration(self):
        return any(g for g in self.groups.all() if g.name == "v2_migration")

    @cached_property
    def is_appsupport(self):
        return any(g for g in self.groups.all() if g.name == "appsupport")

    @cached_property
    def is_pas_service(self):
        return any(g for g in self.groups.all() if g.name == "pas")

    def __str__(self):
        return self.username

    class Meta:
        ordering = ["username"]


class AnonymousMetaxUser(AnonymousUser):
    """Unauthenticated Metax user.

    Fields and properties added for MetaxUser should also be implemented here.
    """

    is_hidden = False
    fairdata_username = None
    csc_projects = []
    admin_organizations = []
    removed = None
    synced = None

    @property
    def is_appsupport(self):
        return False

    @property
    def is_v2_migration(self):
        return False
