import factory
from django.utils import timezone

from apps.users.factories import MetaxUserFactory
from . import models


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Contract
        django_get_or_create = ("url",)

    url = factory.Sequence(lambda n: f"contract-{n}")
    title = factory.Dict({"en": factory.Sequence(lambda n: f"contract-{n}")})
    quota = factory.Faker("random_number")
    valid_until = factory.LazyFunction(timezone.now)


class CatalogHomePageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogHomePage
        django_get_or_create = ("url",)

    title = factory.Dict({"en": factory.Sequence(lambda n: f"catalog-homepage-{n}")})

    @factory.sequence
    def url(self):
        return f"https://catalog-homepage-{self}.fi"


class DatasetPublisherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetPublisher
        django_get_or_create = ("name",)

    name = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-publisher-{n}")})

    @factory.post_generation
    def homepages(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for homepage in extracted:
                self.homepage.add(homepage)


class AccessTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessType
        django_get_or_create = ("url",)

    pref_label = factory.Dict(
        {"en": factory.Sequence(lambda n: f"dataset-access-type-{n}")}
    )

    @factory.sequence
    def url(self):
        return f"https://dataset-access-type-{self}.fi"


class FieldOfScienceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FieldOfScience
        django_get_or_create = ("url",)

    pref_label = factory.Dict(
        {"en": factory.Sequence(lambda n: f"dataset-field-of-science-{n}")}
    )

    @factory.sequence
    def url(self):
        return f"https://dataset-field-of-science-{self}.fi"


class ThemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Theme
        django_get_or_create = ("url",)

    pref_label = factory.Dict(
        {"en": factory.Sequence(lambda n: f"dataset-theme-{n}")}
    )

    @factory.sequence
    def url(self):
        return f"https://dataset-theme-{self}.fi"


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Language
        django_get_or_create = ("url",)

    pref_label = factory.Dict(
        {"en": factory.Sequence(lambda n: f"dataset-language-{n}")}
    )

    @factory.sequence
    def url(self):
        return f"https://dataset-language-{self}.fi"


class LicenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.License
        django_get_or_create = ("url",)

    pref_label = factory.Dict(
        {"en": factory.Sequence(lambda n: f"dataset-license-{n}")}
    )

    @factory.sequence
    def url(self):
        return f"https://dataset-license-{self}.fi"


class AccessRightsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessRights
        django_get_or_create = ("description",)

    access_type = factory.SubFactory(AccessTypeFactory)
    license = factory.RelatedFactory(LicenseFactory)  # create single license
    description = factory.Dict({"en": factory.Faker("paragraph")})


class DataCatalogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataCatalog
        django_get_or_create = ("id",)

    @factory.sequence
    def id(self):
        return f"urn:data-catalog-{self}"

    title = factory.Dict({"en": factory.Sequence(lambda n: f"data-catalog-{n}")})
    publisher = factory.SubFactory(DatasetPublisherFactory)
    access_rights = factory.SubFactory(AccessRightsFactory)
    system_creator = factory.SubFactory(MetaxUserFactory)

    @factory.post_generation
    def languages(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for language in extracted:
                self.language.add(language)


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.File
        django_get_or_create = ("file_path",)

    date_uploaded = factory.LazyFunction(timezone.now)
    file_name = factory.Faker("file_name")
    file_format = factory.Faker("file_extension")
    file_path = factory.Faker("file_path")
    checksum = factory.Faker("md5")
    project_identifier = factory.Faker("numerify", text="#######")
    byte_size = factory.Faker("random_number")

    @factory.post_generation
    def file_format(self, create, extracted, **kwargs):
        if not create:
            return

        self.file_name = str(self.file_path).split("/")[-1]
        self.file_format = str(self.file_name).split(".")[-1]


class DataStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataStorage
        django_get_or_create = ("id",)

    id = factory.Sequence(lambda n: f"data-storage-{n}")


class CatalogRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogRecord

    data_catalog = factory.SubFactory(DataCatalogFactory)
    contract = factory.SubFactory(ContractFactory)


class DatasetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Dataset
        django_get_or_create = ("title",)

    data_catalog = factory.SubFactory(DataCatalogFactory)
    title = factory.Dict({"en": factory.Sequence(lambda n: f"research-dataset-{n}")})
    contract = factory.SubFactory(ContractFactory)
    system_creator = factory.SubFactory(MetaxUserFactory)


class DistributionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Distribution
        django_get_or_create = ("title",)

    id = factory.Faker("uuid4")
    title = factory.Dict({"en": factory.Sequence(lambda n: f"distribution-{n}")})
    license = factory.SubFactory(LicenseFactory)
    access_rights = factory.SubFactory(AccessRightsFactory)
    dataset = factory.SubFactory(DatasetFactory)
    access_service = factory.SubFactory(DataStorageFactory)

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for file in extracted:
                self.files.add(file)
