import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from apps.common.models import CustomSoftDeletableManager, CustomSoftDeletableModel


class MetaxUserManager(UserManager):
    def get_organization_admins(self, organization: str) -> models.QuerySet:
        return self.none()  # TODO: Organization admins not implemented yet


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

    def undelete(self):
        self.removed = None
        self.is_hidden = False
        self.save()

    @cached_property
    def is_v2_migration(self):
        return any(g for g in self.groups.all() if g.name == "v2_migration")

    def __str__(self):
        return self.username

    class Meta:
        ordering = ["username"]
