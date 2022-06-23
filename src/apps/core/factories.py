import factory
from . import models
from django.utils import timezone


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetLanguage
        django_get_or_create = ("url",)

    title = factory.Iterator(
        [
            {"en": "Finnish", "fi": "suomi", "sv": "finska", "und": "suomi"},
            {"en": "Estonian", "fi": "viron kieli", "und": "viron kieli"},
        ]
    )
    url = factory.Iterator(
        ["http://lexvo.org/id/iso639-3/fin", "http://lexvo.org/id/iso639-3/est"]
    )


class CatalogHomePageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogHomePage
        django_get_or_create = ("url",)

    title = factory.Sequence(lambda n: {"en": f"organization-{n}", "fi": f"organisaatio-{n}"})
    url = factory.Sequence(lambda n: f"org-{n}.fi")


class DatasetPublisherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetPublisher
        django_get_or_create = ("name",)

    title = factory.Sequence(lambda n: {"en": f"organization-{n}", "fi": f"organisaatio-{n}"})

    @factory.post_generation
    def homepages(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for homepage in extracted:
                self.homepage.add(homepage)


class DatasetLicenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetLicense
        django_get_or_create = ("url",)


class AccessTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessType
        django_get_or_create = ("url",)

    url = factory.Sequence(lambda n: f"example.com/{n}")


class AccessRightFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessRight
        django_get_or_create = ("description",)

    access_type = factory.SubFactory(AccessTypeFactory)
    license = factory.SubFactory(DatasetLicenseFactory)


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
