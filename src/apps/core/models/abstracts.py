import uuid

from apps.core.helpers import get_technical_metax_user
from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel, SoftDeletableModel


class AbstractBaseModel(TimeStampedModel, SoftDeletableModel):
    """Adds soft-delete and created / modified timestamp functionalities

    Added fields are:
     - created
     - modified
     - is_removed
    """

    removal_date = models.DateTimeField(null=True, blank=True)
    system_creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        default=get_technical_metax_user,
        related_name="%(app_label)s_%(class)ss",
        null=True,
    )

    def delete(self, using=None, soft=True, *args, **kwargs):
        self.removal_date = timezone.now()
        return super().delete(using=using, soft=soft, *args, **kwargs)

    class Meta:
        abstract = True
        get_latest_by = "modified"
        ordering = ["created"]


class AbstractDatasetProperty(AbstractBaseModel):
    """Base class for simple refdata fields with only id and title properties"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(
        max_length=512,
        help_text="valid url to the property definition",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')

    def __str__(self):
        return self.url

    class Meta:
        abstract = True
