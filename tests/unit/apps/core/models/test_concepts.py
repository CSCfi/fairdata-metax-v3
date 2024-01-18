import pytest

from apps.core import factories

pytestmark = [pytest.mark.django_db, pytest.mark.concept]


@pytest.fixture
def concepts():
    return [
        factories.AccessTypeFactory,
        factories.DatasetLicenseFactory,
        factories.EventOutcomeFactory,
        factories.FieldOfScienceFactory,
        factories.FileTypeFactory,
        factories.IdentifierTypeFactory,
        factories.LanguageFactory,
        factories.LifecycleEventFactory,
        factories.SpatialFactory,
        factories.ThemeFactory,
        factories.UseCategoryFactory,
    ]


def test_concept_creation_and_to_string(concepts):
    for concept in concepts:
        saved_concept = concept.create()
        assert saved_concept.id is not None
        assert str(saved_concept) is not None
