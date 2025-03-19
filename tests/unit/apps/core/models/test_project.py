import pytest
from rest_framework import serializers

from apps.core.serializers import ProjectModelSerializer

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def project_json():
    return {
        "participating_organizations": [{"pref_label": {"fi": "testi"}}],
        "funding": [
            {
                "funding_identifier": "rahoitustunniste",
                "funder": {"organization": {"pref_label": {"fi": "rahoittajataho"}}},
            }
        ],
    }


def test_serialize_project(project_json):
    serializer = ProjectModelSerializer(
        data=project_json,
        context={"dataset": None},
    )
    serializer.is_valid(raise_exception=True)
    project = serializer.save()
    assert project.participating_organizations.first().pref_label["fi"] == "testi"
    assert project.funding.first().funding_identifier == "rahoitustunniste"
    assert project.funding.first().funder.organization.pref_label["fi"] == "rahoittajataho"


def test_serialize_project_no_org(project_json):
    project_json["participating_organizations"] = []
    serializer = ProjectModelSerializer(
        data=project_json,
        context={"dataset": None},
    )
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_serialize_project_no_org_migrating(project_json):
    project_json["participating_organizations"] = []
    serializer = ProjectModelSerializer(
        data=project_json,
        context={"dataset": None, "migrating": True},
    )
    serializer.is_valid(raise_exception=True)
    project = serializer.save()
    assert project.participating_organizations.count() == 0
