import factory
from . import models
from django.utils import timezone

class AbstractDatasetPropertyFactory(factory.django.DjangoModelFactory):
    title = {"fi": "otsikko"}
    id = factory.Sequence(lambda n: f"example.com/{n}")

class DataCatalogFactory(AbstractDatasetPropertyFactory):
    class Meta:
        model = models.DataCatalog


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.File

    date_uploaded = factory.LazyFunction(timezone.now)


class DistributionFactory(AbstractDatasetPropertyFactory):
    class Meta:
        model = models.Distribution


class DataStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataStorage

    id = factory.sequence(lambda n: f"service{n}")


class CatalogRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogRecord

    data_catalog = factory.SubFactory(DataCatalogFactory)
