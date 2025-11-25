import factory
from faker import Faker

from .models import MetaxUser, AdminOrganization

faker = Faker()


class MetaxUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetaxUser
        django_get_or_create = ("username",)

    email = factory.Sequence(lambda n: f"email@{n}.com")
    username = factory.Sequence(lambda n: f"test-user-{n}")
    fairdata_username = factory.LazyAttribute(lambda o: o.username)
    id = factory.Faker("uuid4")


class AdminOrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AdminOrganization
        django_get_or_create = ("id", "pref_label", "other_identifier")

    id = factory.Sequence(lambda n: f"admin-org-{n}")
    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"Admin Org {n}")})
    other_identifier = factory.List([factory.sequence(lambda n: f"other-id-{n}")])
