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

    def delete(self, using=None, soft=True, *args, **kwargs):
        self.removal_date = timezone.now()
        self.save()
        return super().delete(using=using, soft=soft, *args, **kwargs)

    class Meta:
        abstract = True
        get_latest_by = "modified"
        ordering = ["created"]


class AbstractDatasetProperty(AbstractBaseModel):
    """Base class for simple refdata fields with only id and title properties"""

    id = models.URLField(
        max_length=512,
        primary_key=True,
        help_text="valid url to the property definition",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')

    def __str__(self):
        return self.id

    class Meta:
        abstract = True