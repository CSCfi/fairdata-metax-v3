import functools
import uuid
from typing import Dict, Iterator

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils import timezone
from model_utils.models import SoftDeletableModel, TimeStampedModel
from polymorphic.models import PolymorphicModel

from apps.common.managers import ProxyBasePolymorphicManager


class SystemCreatorBaseModel(models.Model):
    """Abstact model with system creator field."""

    system_creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)ss",
        null=True,
    )

    class Meta:
        abstract = True


class AbstractBaseModel(SystemCreatorBaseModel, TimeStampedModel, SoftDeletableModel):
    """Adds soft-delete and created / modified timestamp functionalities

    Added fields are:
     - created
     - modified
     - is_removed
    """

    removal_date = models.DateTimeField(null=True, blank=True)

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

    url = models.URLField(
        max_length=512, help_text="valid url to the property definition", null=True, blank=True
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}', blank=True, null=True)
    representation = models.URLField(blank=True, null=True)
    pref_label = HStoreField(blank=True, null=True)
    description = HStoreField(blank=True, null=True)
    in_scheme = models.URLField(max_length=255, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str({k: v for k, v in self.__dict__.items() if v is not None})


class ProxyBasePolymorphicModel(PolymorphicModel):
    """Base class for models instantiated as one of their proxy classes.

    Provider helper functions for choosing proxy class based on value
    defined by proxy_lookup_field.

    Mapping of proxy_lookup_field values to proxy models is determined by
    the proxy_mapping dict.

    Actual class is determined by polymorphic_ctype_id ContentType field.
    """

    objects = ProxyBasePolymorphicManager()

    # Subclasses need to define these values
    proxy_mapping: Dict[str, str]  # map field value to proxy class name
    proxy_lookup_field: str  # field used for determining proxy class

    class Meta:
        abstract = True

    @classmethod
    def get_proxy_instance(cls, *args, **kwargs) -> models.Model:
        """Return new proxy model instance with supplied arguments.

        Proxy model is determined from proxy lookup field value in keyword arguments."""
        if not cls.proxy_lookup_field in kwargs:
            raise ValueError(f"Expected {cls.proxy_lookup_field} keyword argument.")
        model = cls.get_proxy_model(kwargs[cls.proxy_lookup_field])
        return model(*args, **kwargs)

    @classmethod
    @functools.lru_cache
    def get_proxy_model(cls, lookup_value) -> models.Model:
        """Return proxy model corresponding to lookup_value."""
        proxy_name = cls.proxy_mapping.get(lookup_value)
        if not proxy_name:
            raise ValueError(f"Unknown {cls.proxy_lookup_field} value {lookup_value}.")
        for proxy_cls in cls.get_proxy_classes():
            if proxy_name == proxy_cls.__name__:
                return proxy_cls
        raise ValueError(
            f"{cls.__name__} proxy {proxy_name} "
            f"not found for {cls.proxy_lookup_field} value {lookup_value}."
        )

    @classmethod
    def get_proxy_classes(cls) -> Iterator[models.Model]:
        """Get proxy subclasses and also current class if it's a proxy."""
        if cls._meta.proxy:
            yield cls
        yield from cls.get_proxy_subclasses()

    @classmethod
    def get_proxy_subclasses(cls) -> Iterator[models.Model]:
        """Get all proxy subclasses recursively."""
        for subclass in cls.__subclasses__():
            if subclass._meta.proxy:
                yield from subclass.get_proxy_subclasses()
                yield subclass

    def save(self, *args, **kwargs):
        """Raise error if proxy_lookup_field value does not match current model."""
        proxy = self.get_proxy_model(getattr(self, self.proxy_lookup_field))
        is_correct_proxy_model = self.__class__ == proxy
        if not is_correct_proxy_model:
            raise ValueError(
                f"Wrong type {self.__class__.__name__} "
                f"for {self.proxy_lookup_field} value '{self.storage_service}', "
                f"expected {proxy.__name__}."
            )
        return super().save(*args, **kwargs)
