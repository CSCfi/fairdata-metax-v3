import factory
from . import models
from django.utils import timezone


class AbstractDatasetPropertyFactory(factory.django.DjangoModelFactory):
    title = {"fi": "otsikko"}
    url = factory.Sequence(lambda n: f"example.com/{n}")


class DataCatalogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataCatalog

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
