import uuid
from typing import Tuple

from django.contrib.postgres.fields import ArrayField, HStoreField
from django.db import models
from django.utils.translation import gettext as _

from apps.common.helpers import prepare_for_copy
from apps.common.mixins import CopyableModelMixin
from apps.common.models import AbstractBaseModel, AbstractFreeformConcept
from apps.common.serializers.fields import URLReferencedModelField, URLReferencedModelListField
from apps.refdata import models as refdata


def not_implemented_function(*args, **kwargs):
    raise NotImplementedError()


class ConceptProxyMixin:
    """Mixin class for Concept-based proxy models."""

    @classmethod
    def get_serializer_class(cls):
        """Make non-url fields read-only"""
        serializer_class = super(ConceptProxyMixin, cls).get_serializer_class()
        serializer_class.omit_related = True
        serializer_class.Meta.extra_kwargs = {
            field: {"read_only": True} for field in serializer_class.Meta.fields if field != "url"
        }
        serializer_class.Meta.list_serializer_class = URLReferencedModelListField
        serializer_class.save = not_implemented_function
        serializer_class.create = not_implemented_function
        serializer_class.update = not_implemented_function
        return serializer_class

    @classmethod
    def get_serializer_field(cls, **kwargs):
        """Return serializer relation field for concept instances."""
        serializer = cls.get_serializer_class()()
        return URLReferencedModelField(child=serializer, **kwargs)

    class Meta:
        proxy = True


class AccessType(ConceptProxyMixin, refdata.AccessType):
    """Accessibility of the resource"""


class Language(ConceptProxyMixin, refdata.Language):
    """A language of the item.

    This refers to the natural language used for textual metadata (i.e. titles, descriptions, etc)
    of a cataloged resource (i.e. dataset or service) or the textual values of a dataset

    Note:
        Repeat this property if the resource is available in multiple languages.

    Note:
        The value(s) provided for members of a catalog (i.e. dataset or service)
        override the value(s) provided for the catalog if they conflict.

    DRF Property: dcterms:language

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_language
    """


class Theme(ConceptProxyMixin, refdata.Theme):
    """Keyword from KOKO ontology."""


def get_default_license():
    return refdata.License.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/other"
    ).id


class License(ConceptProxyMixin, refdata.License):
    """License from reference data."""


class DatasetLicense(AbstractBaseModel, CopyableModelMixin):
    """A legal document under which the resource is made available.

    RFD Property: dcterms:license

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_license
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    custom_url = models.URLField(max_length=512, blank=True, null=True)
    reference = models.ForeignKey(refdata.License, on_delete=models.CASCADE)
    description = HStoreField(
        help_text='example: {"en":"title", "fi":"otsikko"}', null=True, blank=True
    )

    class Meta:
        ordering = ["created"]
        indexes = [
            models.Index(fields=["custom_url"]),
        ]

    def __str__(self):
        if self.custom_url:
            return self.custom_url
        return self.reference.pref_label.get("en", "")


class FieldOfScience(ConceptProxyMixin, refdata.FieldOfScience):
    """Field of Science classification of resource.

    Source: https://finto.fi/okm-tieteenala/en/
    """


class ResearchInfra(ConceptProxyMixin, refdata.ResearchInfra):
    """Research infrastructure classification of resource.

    Source: http://www.yso.fi/onto/koko/p34158
    """


class LifecycleEvent(ConceptProxyMixin, refdata.LifecycleEvent):
    """Lifecycle event of the resource."""


class EventOutcome(ConceptProxyMixin, refdata.EventOutcome):
    """Event outcome of the resource."""


class IdentifierType(ConceptProxyMixin, refdata.IdentifierType):
    """Identifier type of the resource."""


class UseCategory(ConceptProxyMixin, refdata.UseCategory):
    """Use category type of the resource."""


class FileType(ConceptProxyMixin, refdata.FileType):
    """File type of the resource."""


class Location(ConceptProxyMixin, refdata.Location):
    """Location from reference data."""


class Spatial(AbstractFreeformConcept, CopyableModelMixin):
    """The geographical area covered by the dataset.

    Attributes:
        reference(refdata.License): License's reference
        full_address(models.CharField): The complete address written as a string,
            with or without formatting.
        geographic_name(models.CharField): A geographic name is a proper noun applied to
            a spatial object.
        dataset(Dataset): Dataset ForeignKey relation

    """

    reference = models.ForeignKey(
        refdata.Location, on_delete=models.CASCADE, blank=True, null=True
    )
    full_address = models.CharField(max_length=512, blank=True, null=True)
    geographic_name = models.CharField(max_length=512, blank=True, null=True)
    altitude_in_meters = models.IntegerField(
        blank=True,
        null=True,
        help_text="The altitude of the geographical area (meters from WGS84 reference)",
    )
    custom_wkt = ArrayField(
        models.TextField(),
        blank=True,
        null=True,
        help_text=_("Additional wkt values according to WGS84"),
    )
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="spatial", null=True, blank=True
    )

    @classmethod
    def create_copy(cls, original, dataset=None):
        copy = prepare_for_copy(original)
        if dataset:
            dataset.save()
            copy.dataset = dataset
        copy.save()
        return copy, original

    def __str__(self):
        return self.geographic_name or str(next(iter(self.reference.pref_label.items())))

    class Meta:
        indexes = []


class ContributorType(ConceptProxyMixin, refdata.ContributorType):
    """Project Contributor"""
