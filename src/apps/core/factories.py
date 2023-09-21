import factory
from django.utils import timezone

from apps.actors.factories import OrganizationFactory, PersonFactory
from apps.files.factories import FileStorageFactory
from apps.refdata import models as refdata
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

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-access-type-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-access-type-{self}.fi"


class FieldOfScienceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FieldOfScience
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-field-of-science-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-field-of-science-{self}.fi"


class InfrastructureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ResearchInfra
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-infrastructure-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-infrastructure-{self}.fi"


class LifecycleEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.LifecycleEvent
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"lifecycle-event-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://lifecycle-event-{self}.fi"


class EventOutcomeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.EventOutcome
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"event-outcome-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://event-outcome-{self}.fi"


class FileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FileType
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-file-type-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-file-type-{self}.fi"


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Language
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-language-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-language-{self}.fi"


class LicenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = refdata.License
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"license-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://license-{self}.fi"


class DatasetLicenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetLicense

    reference = factory.SubFactory(
        LicenseFactory, url="http://uri.suomi.fi/codelist/fairdata/license/code/other"
    )


class ThemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Theme
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-theme-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-theme-{self}.fi"


class UseCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UseCategory
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-use-category-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-use-category-{self}.fi"


class AccessRightsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AccessRights
        django_get_or_create = ("description",)

    access_type = factory.SubFactory(AccessTypeFactory)
    license = factory.RelatedFactory(DatasetLicenseFactory)  # create single license
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


class CatalogRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CatalogRecord

    data_catalog = factory.SubFactory(DataCatalogFactory)
    contract = factory.SubFactory(ContractFactory)


class MetadataProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.MetadataProvider

    user = factory.SubFactory(MetaxUserFactory)
    system_creator = factory.SubFactory(MetaxUserFactory)


class DatasetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Dataset
        django_get_or_create = ("title",)

    data_catalog = factory.SubFactory(DataCatalogFactory)
    title = factory.Dict({"en": factory.Sequence(lambda n: f"research-dataset-{n}")})
    contract = factory.SubFactory(ContractFactory)
    access_rights = factory.SubFactory(AccessRightsFactory)
    system_creator = factory.SubFactory(MetaxUserFactory)
    metadata_owner = factory.SubFactory(MetadataProviderFactory)


class DatasetActorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DatasetActor

    dataset = factory.SubFactory(DatasetFactory)
    person = factory.SubFactory(PersonFactory)
    organization = factory.SubFactory(OrganizationFactory)


class FileSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FileSet
        django_get_or_create = ("dataset", "storage")

    dataset = factory.SubFactory(DatasetFactory)
    storage = factory.SubFactory(FileStorageFactory)

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # allow passing files as argument to factory
        if not create:
            return
        if extracted:
            self.files.set(extracted)


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = refdata.Location
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"location-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://location-{self}.fi"


class SpatialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Spatial

    reference = factory.SubFactory(
        LocationFactory, url="http://www.yso.fi/onto/onto/yso/c_9908ce39"
    )


class IdentifierTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = refdata.IdentifierType
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"dataset-identifier-type-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://dataset-identifier-type-{self}.fi"


class ContributorTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ContributorType
        django_get_or_create = ("url",)

    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"contributor-{n}")})
    in_scheme = factory.Faker("url")

    @factory.sequence
    def url(self):
        return f"https://contributor-type-{self}.fi"
