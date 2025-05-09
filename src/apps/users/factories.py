import factory
from faker import Faker

from .models import MetaxUser

faker = Faker()


class MetaxUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetaxUser
        django_get_or_create = ("username",)

    email = factory.Sequence(lambda n: f"email@{n}.com")
    username = factory.Sequence(lambda n: f"test-user-{n}")
    fairdata_username = factory.LazyAttribute(lambda o: o.username)
    id = factory.Faker("uuid4")
