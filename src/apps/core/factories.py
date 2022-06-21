import factory
from . import models
from django.utils import timezone


class AbstractDatasetPropertyFactory(factory.django.DjangoModelFactory):
    title = {"fi": "otsikko"}
    url = factory.Sequence(lambda n: f"example.com/{n}")


class LanguageFactory(AbstractDatasetPropertyFactory):
    class Meta:
        model = models.DatasetLanguage
        django_get_or_create = ("url",)


class CatalogHomePageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogHomePage
        django_get_or_create = ("url",)


class DatasetPublisherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetPublisher
        django_get_or_create = ("name",)


class DatasetLicenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetLicense
        django_get_or_create = ("url",)


class AccessTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessType
        django_get_or_create = ("url",)


class AccessRightFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessRight
        django_get_or_create = ("description",)


class DataCatalogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataCatalog
        django_get_or_create = ("title",)

    id = factory.Sequence(lambda n: f"urn:{n}")
    title = {"fi": "datacatalogi"}


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.File

    date_uploaded = factory.LazyFunction(timezone.now)


class DistributionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Distribution

    title = {"fi": "otsikko"}
    id = factory.Sequence(lambda n: f"distribution{n}")


class DataStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataStorage

    id = factory.sequence(lambda n: f"service{n}")


class CatalogRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogRecord

    data_catalog = factory.SubFactory(DataCatalogFactory)
