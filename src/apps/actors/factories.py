import factory
from django.conf import settings

from .models import Organization


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    id = factory.Faker("uuid4")
    pref_label = factory.Dict({"en": factory.Sequence(lambda n: f"Organization-{n}")})
    in_scheme = settings.ORGANIZATION_SCHEME
    parent = None
    is_reference_data = True

    @factory.lazy_attribute_sequence
    def code(obj, n):
        prefix = ""
        if obj.parent:
            prefix = f"{obj.parent.code}-"
        return f"{prefix}{n}"

    @factory.lazy_attribute
    def url(obj):
        return f"https://{settings.ORGANIZATION_BASE_URI}/{obj.code}"
