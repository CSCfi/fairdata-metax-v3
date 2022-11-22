from apps.refdata import models as refdata


class ConceptProxyMixin:
    """Mixin class for Concept-based proxy models."""

    @classmethod
    def get_serializer(cls):
        """Make non-url fields read-only"""
        serializer_class = super(ConceptProxyMixin, cls).get_serializer()
        serializer_class.Meta.extra_kwargs = {
            field: {"read_only": True}
            for field in serializer_class.Meta.fields
            if field != "url"
        }
        return serializer_class

    class Meta:
        proxy = True


class AccessType(ConceptProxyMixin, refdata.AccessType):
    """Accessibility of the resource"""


class Language(ConceptProxyMixin, refdata.Language):
    """A language of the item.

    This refers to the natural language used for textual metadata (i.e. titles, descriptions, etc)
    of a cataloged resource (i.e. dataset or service) or the textual values of a dataset distribution

    Note:
        Repeat this property if the resource is available in multiple languages.

    Note:
        The value(s) provided for members of a catalog (i.e. dataset or service)
        override the value(s) provided for the catalog if they conflict.

    Note:
        If representations of a dataset are available for each language separately,
        define an instance of dcat:Distribution for each language and describe the specific language of each
        distribution using dcterms:language (i.e. the dataset will have multiple dcterms:language values and
        each distribution will have just one as the value of its dcterms:language property).

    DRF Property: dcterms:language

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_language
    """


class Keyword(ConceptProxyMixin, refdata.Keyword):
    """Keyword from KOKO ontology."""


class License(ConceptProxyMixin, refdata.License):
    """A legal document under which the resource is made available.

    RFD Property: dcterms:license

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Property:resource_license
    """


class FieldOfScience(ConceptProxyMixin, refdata.FieldOfScience):
    """Field of Science classification of resource.

    Source: https://finto.fi/okm-tieteenala/en/
    """
