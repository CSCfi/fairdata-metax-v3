import pytest
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from apps.actors.factories import OrganizationFactory
from apps.actors.models import Organization


@pytest.fixture
def organization_tree():
    OrganizationFactory.reset_sequence()
    org0 = OrganizationFactory.create()
    org1 = OrganizationFactory.create()
    org1_2 = OrganizationFactory.create(parent=org1)
    org1_2_3 = OrganizationFactory.create(parent=org1_2)
    org1_2_4 = OrganizationFactory.create(parent=org1_2)
    org1_5 = OrganizationFactory.create(parent=org1)


def get_code_trees(orgs):
    """Convert org tree into nested dict, key from code, value from children"""

    codes = {}
    for org in orgs:
        # list parents first
        while parent := org.get("parent"):
            if not parent.get("children"):
                parent["children"] = [org]
            org = parent

        def recurse(node):
            node_codes = {}
            children = node.get("children", [])
            for child in children:
                node_codes[child["code"]] = recurse(child)
            return node_codes

        codes[org["code"]] = recurse(org)
    return codes


@pytest.fixture
def check_org_trees(organization_tree):
    """Check that response for organization contains correct organizations based on codes."""

    def func(org_code, expected_code_tree):
        client = APIClient()
        code_trees = {}
        if org_code:
            # single org
            org_id = Organization.available_objects.get(code=org_code).id
            resp = client.get(
                f"{reverse('organization-detail', args=[org_id])}", {"expand_children": True}
            )
            assert resp.status_code == 200
            code_trees = get_code_trees([resp.data])
        else:
            # list of orgs
            resp = client.get(f"{reverse('organization-list')}", {"expand_children": True})
            assert resp.status_code == 200
            code_trees = get_code_trees(resp.data["results"])
        assert code_trees == expected_code_tree

    return func


@pytest.mark.django_db
def test_get_org_list(check_org_trees):
    check_org_trees(None, {"0": {}, "1": {"1-2": {"1-2-3": {}, "1-2-4": {}}, "1-5": {}}})


@pytest.mark.django_db
def test_get_main_org(check_org_trees):
    check_org_trees("1", {"1": {"1-2": {"1-2-3": {}, "1-2-4": {}}, "1-5": {}}})


@pytest.mark.django_db
def test_get_sub_org(check_org_trees):
    check_org_trees("1-2", {"1": {"1-2": {"1-2-3": {}, "1-2-4": {}}}})


@pytest.mark.django_db
def test_get_sub_sub_org(check_org_trees):
    check_org_trees("1-2-3", {"1": {"1-2": {"1-2-3": {}}}})
