import functools
import re
import uuid
import warnings
from typing import Dict, Iterator

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.query import QuerySet
from django.utils import timezone
from model_utils.models import TimeStampedModel
from polymorphic.models import PolymorphicModel

from apps.common.managers import ProxyBasePolymorphicManager


class SystemCreatorBaseModel(models.Model):
    """Abstact model with system creator field."""

    system_creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)ss",
        null=True,
        editable=False,
        blank=True,
    )

    class Meta:
        abstract = True


class CustomSoftDeletableQuerySet(QuerySet):
    """Customized version of model_utils SoftDeletableQuerySet
    QuerySet for SoftDeletableModel. Instead of removing instance sets
    its ``removed`` field to timestamp.
    """

    def delete(self):
        """
        Soft delete objects from queryset (set their ``removed``
        field to current timestamp)
        """
        self.update(removed=timezone.now())


class CustomSoftDeletableManager(models.Manager):
    """Customized version of model_utils SoftDeletableManager
    Manager that limits the queryset by default to show only not removed
    instances of model.
    """

    _queryset_class = CustomSoftDeletableQuerySet

    def __init__(self, *args, _emit_deprecation_warnings=False, **kwargs):
        self.emit_deprecation_warnings = _emit_deprecation_warnings
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        """
        Return queryset limited to not removed entries.
        """

        if self.emit_deprecation_warnings:
            warning_message = (
                "{0}.objects model manager will include soft-deleted objects in an "
                "upcoming release; please use {0}.available_objects to continue "
                "excluding soft-deleted objects. See "
                "https://django-model-utils.readthedocs.io/en/stable/models.html"
                "#softdeletablemodel for more information."
            ).format(self.model.__class__.__name__)
            warnings.warn(warning_message, DeprecationWarning)

        kwargs = {"model": self.model, "using": self._db}
        if hasattr(self, "_hints"):
            kwargs["hints"] = self._hints

        return self._queryset_class(**kwargs).filter(removed__isnull=True)


class CustomSoftDeletableModel(models.Model):
    """Customized version of model_utils SoftDeletableModel"""

    objects = CustomSoftDeletableManager(_emit_deprecation_warnings=True)
    available_objects = CustomSoftDeletableManager()
    all_objects = models.Manager()
    removed = models.DateTimeField(null=True, blank=True, editable=False)

    def delete(self, using=None, soft=True, *args, **kwargs):
        """
        Soft delete object (set its ``removed`` field to current time).
        Actually delete object if setting ``soft`` to False.
        """
        if soft:
            self.removed = timezone.now()
            self.save(using=using)
        else:
            return super().delete(using=using, *args, **kwargs)

    class Meta:
        abstract = True


class AbstractBaseModel(SystemCreatorBaseModel, TimeStampedModel, CustomSoftDeletableModel):
    """Adds soft-delete and created / modified timestamp functionalities

    Added fields are:
     - created
     - modified
     - removed
    """

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


# Very permissive regex for validating "type/subtype" style string
# https://www.rfc-editor.org/rfc/rfc2045#section-5.1
mediatype_regex = re.compile(r".+/.+")


class MediaTypeValidator(RegexValidator):
    """Validator for media types (formerly MIME types)."""

    def __init__(self, **kwargs):
        super().__init__(regex=mediatype_regex, **kwargs)
