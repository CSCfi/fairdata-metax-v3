import uuid

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
        related_name="%(app_label)s_%(class)ss",
        null=True,
    )

    def delete(self, using=None, soft=True, *args, **kwargs):
        """Override delete method to add removal_date

        Args:
            using ():
            soft (bool): is the instance soft deleted

        Returns:
            (int): count of deleted objects

        """
        self.removal_date = timezone.now()
        return super().delete(using=using, soft=soft, *args, **kwargs)

    class Meta:
        abstract = True
        get_latest_by = "modified"
        ordering = ["created"]


class AbstractDatasetProperty(AbstractBaseModel):
    """Base class for simple refdata fields with only id and title properties

    Attributes:
        title (HstoreField): property title
        url (models.URLField): property url
    """

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


class AbstractFreeformConcept(AbstractDatasetProperty):
    """Permissive version of concept object with added custom fields

    Necessary for objects that do not conform to the requirements of reference data. Should only be used with core-app.

    Attributes:
        title (HstoreField): property title, usually this would be pref_label in reference data
        representation (models.URLField): representation of the concept
        pref_label (HStoreField): title of the concept
        description (HStoreField): detailed freeform description of the concept
        in_scheme (models.URLField): scheme of the concept
    """

    title = HStoreField(
        help_text='example: {"en":"title", "fi":"otsikko"}', blank=True, null=True
    )
    representation = models.URLField(blank=True, null=True)
    pref_label = HStoreField(blank=True, null=True)
    description = HStoreField(blank=True, null=True)
    in_scheme = models.URLField(max_length=255, null=True, blank=True)

    class Meta:
        abstract = True
