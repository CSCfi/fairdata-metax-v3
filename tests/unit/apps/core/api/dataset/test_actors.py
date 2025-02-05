import json
import logging
import uuid
from unittest.mock import ANY

import pytest
from django.test.client import Client
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict, matchers

from apps.actors.models import Organization
from apps.core.models import OtherIdentifier
from apps.core.models.concepts import IdentifierType
from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def dataset(admin_client, dataset_a_json, reference_data, data_catalog):
    del dataset_a_json["language"]
    del dataset_a_json["field_of_science"]
    del dataset_a_json["theme"]
    dataset_a_json["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    return res.data


@pytest.fixture
def patch_dataset(admin_client, dataset):
    def _patch(data: dict, expected_status=200):
        resp = admin_client.patch(
            f"/v3/datasets/{dataset['id']}", data, content_type="application/json"
        )
        if resp.status_code != expected_status:
            print(resp.data)
        assert resp.status_code == expected_status
        return resp.data

    return _patch


@pytest.fixture
def another_dataset_with_actors(admin_client, dataset_b_json, reference_data, data_catalog):
    del dataset_b_json["language"]
    del dataset_b_json["field_of_science"]
    del dataset_b_json["theme"]

    teppo_org = {"pref_label": {"en": "teppo org"}}
    matti_org = {"pref_label": {"en": "matti org"}}
    dataset_b_json["actors"] = [
        {"person": {"name": "teppo"}, "organization": teppo_org},
        {"person": {"name": "matti"}, "organization": matti_org},
    ]

    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    return res.data


def test_create_actor(patch_dataset):
    org = {"pref_label": {"en": "organization"}}
    data = patch_dataset(
        {"actors": [{"person": {"name": "teppo"}, "organization": org, "roles": ["creator"]}]}
    )
    assert data["actors"] == [
        matchers.DictContaining(
            {"person": matchers.DictContaining({"name": "teppo"}), "roles": ["creator"]}
        )
    ]


def test_create_actors_with_multiple_roles_identical(patch_dataset):
    org = {"pref_label": {"en": "organization"}}
    data = patch_dataset(
        {
            "actors": [
                {"person": {"name": "teppo"}, "organization": org, "roles": ["creator"]},
                {"person": {"name": "teppo"}, "organization": org, "roles": ["publisher"]},
            ]
        }
    )
    assert data["actors"] == [
        matchers.DictContaining(
            {
                "person": matchers.DictContaining({"name": "teppo"}),
                "organization": matchers.DictContaining(org),
                "roles": ["creator", "publisher"],
            }
        )
    ]


def test_create_actors_with_multiple_roles_different_person_name(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {"person": {"name": "matti"}, **org, "roles": ["creator"]},
                {"person": {"name": "teppo"}, **org, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "person": {"name": "matti"},
                "roles": ["creator"],
            },
            {
                "person": {"name": "teppo"},
                "roles": ["publisher"],
            },
        ],
        data["actors"],
    )
    assert data["actors"][0]["person"]["id"] != data["actors"][1]["person"]["id"]


def test_create_actors_with_multiple_roles_same_id(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {"id": "#a1", "person": {"name": "teppo"}, **org, "roles": ["creator"]},
                {"id": "#a1", "person": {"name": "teppo"}, **org, "roles": ["publisher"]},
            ]
        }
    )
    assert data["actors"] == [
        matchers.DictContaining(
            {
                "person": matchers.DictContaining({"name": "teppo"}),
                "organization": matchers.DictContaining(org["organization"]),
                "roles": ["creator", "publisher"],
            }
        )
    ]


def test_create_actors_with_multiple_roles_different_id(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {"id": "#a1", "person": {"name": "teppo"}, **org, "roles": ["creator"]},
                {"id": "#a2", "person": {"name": "teppo"}, **org, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "person": matchers.DictContaining({"name": "teppo"}),
                "roles": ["creator"],
            },
            {
                "person": matchers.DictContaining({"name": "teppo"}),
                "roles": ["publisher"],
            },
        ],
        data["actors"],
    )


def test_create_actors_with_multiple_roles_same_person_id(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {"person": {"id": "#teppo", "name": "teppo"}, **org, "roles": ["creator"]},
                {"person": {"id": "#teppo", "name": "teppo"}, **org, "roles": ["publisher"]},
            ]
        }
    )
    assert data["actors"] == [
        matchers.DictContaining(
            {
                "person": matchers.DictContaining({"name": "teppo"}),
                "roles": ["creator", "publisher"],
            }
        )
    ]


def test_create_actors_with_multiple_roles_different_person_id(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {**org, "person": {"id": "#teppo", "name": "teppo"}, "roles": ["creator"]},
                {**org, "person": {"id": "#otherteppo", "name": "teppo"}, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "person": {"name": "teppo"},
                "roles": ["creator"],
            },
            {
                "person": {"name": "teppo"},
                "roles": ["publisher"],
            },
        ],
        data["actors"],
    )
    assert data["actors"][0]["person"]["id"] != data["actors"][1]["person"]["id"]


def test_create_actors_with_multiple_roles_same_org_id(patch_dataset):
    org = {"pref_label": {"en": "organization"}}
    data = patch_dataset(
        {
            "actors": [
                {"organization": {**org, "id": "#org1"}, "roles": ["creator"]},
                {"organization": {**org, "id": "#org1"}, "roles": ["publisher"]},
            ]
        }
    )
    assert data["actors"] == [
        matchers.DictContaining(
            {
                "organization": matchers.DictContaining(org),
                "roles": ["creator", "publisher"],
            }
        )
    ]


def test_create_actors_with_multiple_roles_different_org_id(patch_dataset):
    org = {"pref_label": {"en": "organization"}}
    data = patch_dataset(
        {
            "actors": [
                {"organization": {**org, "id": "#org1"}, "roles": ["creator"]},
                {"organization": {**org, "id": "#org2"}, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "organization": org,
                "roles": ["creator"],
            },
            {
                "organization": org,
                "roles": ["publisher"],
            },
        ],
        data["actors"],
    )
    assert data["actors"][0]["organization"]["id"] != data["actors"][1]["organization"]["id"]


def test_create_actors_with_multiple_roles_different_org_name(patch_dataset):
    org1 = {"pref_label": {"en": "organization 1"}}
    org2 = {"pref_label": {"en": "organization 2"}}
    data = patch_dataset(
        {
            "actors": [
                {"organization": {**org1}, "roles": ["creator"]},
                {"organization": {**org2}, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "organization": org1,
                "roles": ["creator"],
            },
            {
                "organization": org2,
                "roles": ["publisher"],
            },
        ],
        data["actors"],
    )
    assert data["actors"][0]["organization"]["id"] != data["actors"][1]["organization"]["id"]


def test_create_actors_with_multiple_roles_identical_multilevel_org(patch_dataset):
    org = {
        "pref_label": {"en": "subsub"},
        "parent": {"pref_label": {"en": "sub"}, "parent": {"pref_label": {"en": "top"}}},
    }
    data = patch_dataset(
        {
            "actors": [
                {"organization": org, "roles": ["creator"]},
                {"organization": org, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "organization": org,
                "roles": ["creator", "publisher"],
            },
        ],
        data["actors"],
    )


def flatten(org):
    orgs = []
    while org:
        next_org = org.pop("parent", None)
        orgs.append(org)
        org = next_org
    return list(orgs)


def test_create_multilevel_org_repeated_name(patch_dataset):
    """Check that orgs won't recurse infinitely."""
    baseorg = {
        "pref_label": {"en": "org"},
    }
    org = {**baseorg, "parent": {**baseorg, "parent": {**baseorg}}}
    data = patch_dataset({"actors": [{"organization": org}]})
    flat = flatten(data["actors"][0]["organization"])
    assert len(flat) == 3
    assert len({o["id"] for o in flat}) == 3  # all orgs have different id
    assert sum(1 for o in flat if o["pref_label"] == baseorg["pref_label"]) == 3


def test_create_multiple_child_orgs(patch_dataset):
    parent = {"pref_label": {"en": "parent"}}
    sub1 = {"pref_label": {"en": "sub1"}, "parent": {**parent}}
    sub2 = {"pref_label": {"en": "sub2"}, "parent": {**parent}}

    data = patch_dataset(
        {
            "actors": [
                {"organization": sub1},
                {"organization": sub2},
            ]
        }
    )
    assert_nested_subdict(sub1, data["actors"][0]["organization"])
    assert_nested_subdict(sub2, data["actors"][1]["organization"])
    data["actors"][0]["organization"] != data["actors"][1]["organization"]
    data["actors"][0]["organization"]["parent"] == data["actors"][1]["organization"]["parent"]

    parent_id = data["actors"][0]["organization"]["parent"]["id"]
    assert Organization.objects.get(id=parent_id).children.count() == 2


def test_create_actors_with_multiple_roles_other_person_has_only_id(patch_dataset):
    org = {"pref_label": {"en": "organization"}}
    data = patch_dataset(
        {
            "actors": [
                {"person": {"id": "#1", "name": "teppo"}, "organization": org},
                {"person": {"id": "#1"}, "organization": org, "roles": ["publisher"]},
            ]
        }
    )
    assert data["actors"] == [
        matchers.DictContaining(
            {
                "person": matchers.DictContaining({"name": "teppo"}),
                "organization": matchers.DictContaining(org),
                "roles": ["publisher"],
            }
        )
    ]


def test_create_actors_with_multiple_roles_other_org_has_only_id(patch_dataset):
    org = {"id": "#org", "pref_label": {"en": "organization"}}
    data = patch_dataset(
        {
            "actors": [
                {"organization": org},
                {"organization": {"id": "#org"}, "roles": ["publisher"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                "organization": {"pref_label": org["pref_label"]},
                "roles": ["publisher"],
            }
        ],
        data["actors"],
    )


@pytest.fixture
def existing_actors(patch_dataset):
    teppo_org = {"pref_label": {"en": "teppo org"}}
    matti_org = {"pref_label": {"en": "matti org"}}
    data = patch_dataset(
        {
            "actors": [
                {"person": {"name": "teppo"}, "organization": teppo_org},
                {"person": {"name": "matti"}, "organization": matti_org},
            ]
        }
    )
    return data["actors"]


def test_update_existing_actor_roles(patch_dataset, existing_actors):
    data = patch_dataset(
        {
            "actors": [
                {"id": existing_actors[0]["id"], "roles": ["contributor"]},
            ]
        }
    )
    assert_nested_subdict(
        [
            {
                **existing_actors[0],
                "roles": ["contributor"],
            }
        ],
        data["actors"],
    )


def test_update_actor_order(patch_dataset, existing_actors):
    leena_org = {"pref_label": {"en": "leena org"}}
    new_person = {"person": {"name": "leena"}, "organization": leena_org}
    data = patch_dataset(
        {
            "actors": [
                {"id": existing_actors[1]["id"]},
                new_person,
                {"id": existing_actors[0]["id"]},
                {"id": existing_actors[1]["id"]},  # should get merged with first actor
            ]
        }
    )
    assert_nested_subdict(
        [
            existing_actors[1],
            new_person,
            existing_actors[0],
        ],
        data["actors"],
    )


def test_update_existing_organizations(patch_dataset, existing_actors):
    org1 = {**existing_actors[0]["organization"]}
    org1["email"] = "testi@example.com"
    data = patch_dataset(
        {
            "actors": [
                {"person": existing_actors[0]["person"], "organization": org1},
                {"person": existing_actors[1]["person"], "organization": {"id": org1["id"]}},
            ]
        }
    )
    assert_nested_subdict(
        [
            {"person": existing_actors[0]["person"], "organization": org1},
            {"person": existing_actors[1]["person"], "organization": org1},
        ],
        data["actors"],
    )


def test_update_existing_persons(patch_dataset, existing_actors):
    person1 = {**existing_actors[0]["person"]}
    person1["email"] = "testi@example.com"
    data = patch_dataset(
        {
            "actors": [
                {"person": person1, "organization": existing_actors[0]["organization"]},
                {
                    "person": existing_actors[1]["person"],
                    "organization": existing_actors[1]["organization"],
                },
            ]
        }
    )
    assert_nested_subdict(
        [
            {"person": person1, "organization": existing_actors[0]["organization"]},
            {
                "person": existing_actors[1]["person"],
                "organization": existing_actors[1]["organization"],
            },
        ],
        data["actors"],
    )


def test_reuse_existing_organization_role(patch_dataset):
    org = {"pref_label": {"en": "Organization"}}
    data = patch_dataset({"actors": [{"organization": org, "roles": ["creator"]}]})
    data = patch_dataset({"actors": [{"id": data["actors"][0]["id"]}]})
    assert data["actors"][0]["roles"] == ["creator"]


def test_clear_existing_organization_role(patch_dataset):
    org = {"pref_label": {"en": "Organization"}}
    data = patch_dataset({"actors": [{"organization": org, "roles": ["creator"]}]})
    data = patch_dataset({"actors": [{"id": data["actors"][0]["id"], "roles": []}]})
    assert data["actors"][0]["roles"] == []


def test_set_organization_role_null(patch_dataset):
    org = {"pref_label": {"en": "Organization"}}
    data = patch_dataset({"actors": [{"organization": org, "roles": None}]}, expected_status=400)
    assert data["actors"][0]["roles"] == ["This field may not be null."]


def test_create_actor_with_refdata_org_by_url(patch_dataset, organization_reference_data):
    org = organization_reference_data[0]
    data = patch_dataset({"actors": [{"organization": {"url": org.url}}]})
    assert_nested_subdict({"organization": {"pref_label": org.pref_label}}, data["actors"][0])


def test_create_actor_with_refdata_org_by_id(patch_dataset, organization_reference_data):
    org = organization_reference_data[0]
    data = patch_dataset({"actors": [{"organization": {"id": org.id}}]})
    assert_nested_subdict({"organization": {"pref_label": org.pref_label}}, data["actors"][0])


def test_create_actor_with_refdata_org_by_id_and_url(patch_dataset, organization_reference_data):
    org = organization_reference_data[0]
    data = patch_dataset({"actors": [{"organization": {"id": org.id, "url": org.url}}]})
    assert_nested_subdict({"organization": {"pref_label": org.pref_label}}, data["actors"][0])


def test_create_actor_with_invalid_refdata_org(patch_dataset, organization_reference_data):
    org = organization_reference_data[0]
    data = patch_dataset(
        {"actors": [{"organization": {"url": org.url + "höpö"}}]}, expected_status=400
    )
    assert (
        str(data["actors"][0]["organization"]["url"])
        == "Reference organization matching query does not exist."
    )


def test_create_actor_with_invalid_refdata_org_ok_url_bad_id(
    patch_dataset, organization_reference_data
):
    bad_id = uuid.UUID(int=0)
    org = organization_reference_data[0]
    data = patch_dataset(
        {"actors": [{"organization": {"id": bad_id, "url": org.url + "höpö"}}]},
        expected_status=400,
    )
    assert (
        str(data["actors"][0]["organization"]["url"])
        == "Reference organization matching query does not exist."
    )


def test_create_actor_with_refdata_org_parent(patch_dataset, organization_reference_data):
    org = organization_reference_data[0]
    data = patch_dataset(
        {
            "actors": [
                {"organization": {"pref_label": {"en": "Sub-org"}, "parent": {"url": org.url}}}
            ]
        }
    )
    assert_nested_subdict(
        {
            "organization": {
                "pref_label": {"en": "Sub-org"},
                "parent": {"pref_label": org.pref_label},
            }
        },
        data["actors"][0],
    )


def test_create_actor_with_refdata_org_ignore_parent(patch_dataset, organization_reference_data):
    """'Reparenting' a reference organization should not be possible."""
    org = organization_reference_data[0]
    data = patch_dataset(
        {
            "actors": [
                {"organization": {"url": org.url, "parent": {"pref_label": {"en": "Sub-org"}}}}
            ]
        }
    )
    assert data["actors"][0]["organization"]["pref_label"] == org.pref_label
    assert data["actors"][0]["organization"].get("parent") is None


def test_actor_does_not_exist(patch_dataset):
    actor_id = 1
    data = patch_dataset({"actors": [{"id": actor_id}]}, expected_status=400)
    assert "DatasetActor does not exist in dataset" in str(data["actors"][0]["id"])


def test_person_does_not_exist(patch_dataset):
    person_id = 1
    data = patch_dataset({"actors": [{"person": {"id": person_id}}]}, expected_status=400)
    assert "Person does not exist in dataset" in str(data["actors"][0]["person"]["id"])


def test_organization_does_not_exist(patch_dataset):
    organization_id = uuid.UUID(int=0)
    data = patch_dataset(
        {"actors": [{"organization": {"id": organization_id}}]}, expected_status=400
    )
    assert "Organization is not reference data and does not exist in dataset" in str(
        data["actors"][0]["organization"]["id"]
    )


def test_actor_from_another_dataset(patch_dataset, another_dataset_with_actors):
    actor_id = another_dataset_with_actors["actors"][0]["id"]
    data = patch_dataset({"actors": [{"id": actor_id}]}, expected_status=400)
    assert "DatasetActor does not exist in dataset" in str(data["actors"][0]["id"])


def test_person_from_another_dataset(patch_dataset, another_dataset_with_actors):
    person_id = another_dataset_with_actors["actors"][0]["person"]["id"]
    data = patch_dataset({"actors": [{"person": {"id": person_id}}]}, expected_status=400)
    assert "Person does not exist in dataset" in str(data["actors"][0]["person"]["id"])


def test_organization_from_another_dataset(patch_dataset, another_dataset_with_actors):
    organization_id = another_dataset_with_actors["actors"][0]["organization"]["id"]
    data = patch_dataset(
        {"actors": [{"organization": {"id": organization_id}}]}, expected_status=400
    )
    assert "Organization is not reference data and does not exist in dataset" in str(
        data["actors"][0]["organization"]["id"]
    )


def test_create_actor_conflicting_person(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {"id": "#actor", "person": {"name": "matti"}, **org},
                {"id": "#actor", "person": {"name": "teppo"}, **org},
            ]
        },
        expected_status=400,
    )
    assert data["actors"] == [
        {},
        {
            "id": "Conflicting data for DatasetActor #actor",
            "person": "Value conflicts with another in request",
        },
    ]


def test_create_actor_conflicting_org(patch_dataset):
    data = patch_dataset(
        {
            "actors": [
                {"id": "#actor", "organization": {"pref_label": {"en": "org1"}}},
                {"id": "#actor", "organization": {"pref_label": {"en": "org2"}}},
            ]
        },
        expected_status=400,
    )
    assert data["actors"] == [
        {},
        {
            "id": "Conflicting data for DatasetActor #actor",
            "organization": "Value conflicts with another in request",
        },
    ]


def test_create_actor_person_conflicting_name(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [
                {"person": {"id": "#matti", "name": "matti"}, **org},
                {"person": {"id": "#matti", "name": "teppo"}, **org},
            ]
        },
        expected_status=400,
    )
    assert data["actors"] == [
        {},
        {
            "person": {
                "id": "Conflicting data for Person #matti",
                "name": "Value conflicts with another in request",
            }
        },
    ]


def test_create_actor_organization_conflicting_pref_label(patch_dataset):
    data = patch_dataset(
        {
            "actors": [
                {"organization": {"id": "#org", "pref_label": {"en": "org1"}}},
                {"organization": {"id": "#org", "pref_label": {"en": "org2"}}},
            ]
        },
        expected_status=400,
    )
    assert data["actors"] == [
        {},
        {
            "organization": {
                "id": "Conflicting data for Organization #org",
                "pref_label": "Value conflicts with another in request",
            }
        },
    ]


def test_existing_actor_conflicting_person(patch_dataset, existing_actors):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    actor_id = existing_actors[0]["id"]
    data = patch_dataset(
        {
            "actors": [
                {"id": actor_id, "person": {"name": "matti"}, **org},
                {"id": actor_id, "person": {"name": "teppo"}, **org},
            ]
        },
        expected_status=400,
    )
    assert data["actors"] == [
        {},
        {
            "id": f"Conflicting data for DatasetActor {actor_id}",
            "person": "Value conflicts with another in request",
        },
    ]


def test_create_empty_actor(patch_dataset):
    data = patch_dataset(
        {"actors": [{}]},
        expected_status=400,
    )
    assert data["actors"][0] == {"organization": "This field is required"}


def test_create_empty_person(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {"actors": [{"person": {}}]},
        expected_status=400,
    )
    assert data["actors"][0] == {"organization": "This field is required"}


def test_create_empty_organization(patch_dataset):
    data = patch_dataset(
        {"actors": [{"organization": {}}]},
        expected_status=400,
    )
    assert data["actors"][0]["organization"] == {"pref_label": "Field is required."}


def test_create_actor_no_person_or_org(patch_dataset):
    data = patch_dataset(
        {"actors": [{"roles": ["creator"]}]},
        expected_status=400,
    )
    assert data["actors"][0] == {"organization": "This field is required"}


def test_update_actor_no_person_or_org(patch_dataset, existing_actors):
    actor_id = existing_actors[0]["id"]
    data = patch_dataset(
        {"actors": [{"id": actor_id, "person": None, "organization": None}]},
        expected_status=400,
    )
    assert data["actors"][0] == {"organization": "This field is required"}


def test_update_organization_no_pref_label(patch_dataset, existing_actors):
    organization_id = existing_actors[0]["organization"]["id"]
    data = patch_dataset(
        {"actors": [{"organization": {"id": organization_id, "pref_label": None}}]},
        expected_status=400,
    )
    assert data["actors"][0]["organization"] == {"pref_label": ["This field may not be null."]}


def test_update_organization_empty_pref_label(patch_dataset, existing_actors):
    organization_id = existing_actors[0]["organization"]["id"]
    data = patch_dataset(
        {"actors": [{"organization": {"id": organization_id, "pref_label": {}}}]},
        expected_status=400,
    )
    assert data["actors"][0]["organization"] == {
        "pref_label": ["This dictionary may not be empty."]
    }


def test_update_person_no_name(patch_dataset, existing_actors):
    person_id = existing_actors[0]["person"]["id"]
    data = patch_dataset(
        {"actors": [{"person": {"id": person_id, "name": None}}]},
        expected_status=400,
    )
    assert data["actors"][0]["person"] == {"name": ["This field may not be null."]}


def test_update_person_empty_name(patch_dataset, existing_actors):
    person_id = existing_actors[0]["person"]["id"]
    data = patch_dataset(
        {"actors": [{"person": {"id": person_id, "name": ""}}]},
        expected_status=400,
    )
    assert data["actors"][0]["person"] == {"name": ["This field may not be blank."]}


def test_create_provenance_actor(patch_dataset):
    actor = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {"provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}]},
    )
    assert_nested_subdict(actor, data["provenance"][0]["is_associated_with"][0])


def test_create_provenance_and_role_refdata_actor(patch_dataset, organization_reference_data):
    org = organization_reference_data[0]
    actor = {
        "organization": {
            "id": org.id,
            "pref_label": {"en": "blah blah"},  # should be ignored
        }
    }
    data = patch_dataset(
        {
            "actors": [actor],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        }
    )
    assert_nested_subdict({"organization": {"pref_label": org.pref_label}}, data["actors"][0])


def test_create_provenance_and_role_actor(patch_dataset):
    actor = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
    )
    assert_nested_subdict(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
        data,
    )


def test_create_provenance_actor_by_id(patch_dataset):
    actor = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [{**actor, "id": "#actor", "roles": ["creator"]}],
            "provenance": [
                {"description": {"en": "provenance"}, "is_associated_with": [{"id": "#actor"}]}
            ],
        },
    )
    assert_nested_subdict(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
        data,
    )


def test_create_provenance_actor_by_id_error(patch_dataset):
    org = {"organization": {"pref_label": {"en": "organization"}}}

    data = patch_dataset(
        {
            "actors": [{"id": "#actor", "person": {}, **org, "roles": ["creator"]}],
            "provenance": [
                {"description": {"en": "provenance"}, "is_associated_with": [{"id": "#actor"}]}
            ],
        },
        expected_status=400,
    )
    assert data["actors"][0] == {"person": {"name": "Field is required."}}
    assert data["provenance"][0]["is_associated_with"][0] == {
        "person": {"name": "Field is required."}
    }


def test_create_actor_by_provenance_actor_id(patch_dataset):
    actor = {"organization": {"pref_label": {"en": "organization"}}}
    data = patch_dataset(
        {
            "actors": [{"id": "#actor", "roles": ["creator"]}],
            "provenance": [
                {
                    "description": {"en": "provenance"},
                    "is_associated_with": [{**actor, "id": "#actor"}],
                }
            ],
        },
    )
    assert_nested_subdict(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
        data,
    )


def test_create_provenance_actor_by_existing_actor_id(patch_dataset):
    actor = {
        "organization": {"pref_label": {"en": "Org"}},
        "person": {"name": "teppo"},
    }
    data = patch_dataset(
        {
            "actors": [
                {**actor, "roles": ["creator"]},
            ]
        }
    )
    actor_id = data["actors"][0]["id"]
    data = patch_dataset(
        {
            "provenance": [  # patch only provenance
                {
                    "description": {"en": "provenance"},
                    "is_associated_with": [{"id": actor_id}],
                }
            ],
        },
    )
    assert_nested_subdict(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
        data,
    )


def test_create_actor_by_existing_provenance_actor_id(patch_dataset):
    actor = {
        "organization": {"pref_label": {"en": "Org"}},
        "person": {"name": "teppo"},
    }
    data = patch_dataset(
        {
            "provenance": [  # patch only provenance
                {
                    "description": {"en": "provenance"},
                    "is_associated_with": [actor],
                }
            ],
        },
    )
    actor_id = data["provenance"][0]["is_associated_with"][0]["id"]
    data = patch_dataset(
        {
            "actors": [
                {"id": actor_id, "roles": ["creator"]},
            ]
        }
    )
    assert_nested_subdict(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
        data,
    )


def test_existing_provenance_person_and_org(patch_dataset):
    actor = {
        "organization": {"pref_label": {"en": "Org"}},
        "person": {"name": "teppo"},
    }
    data = patch_dataset(
        {
            "provenance": [  # patch only provenance
                {
                    "description": {"en": "provenance"},
                    "is_associated_with": [actor],
                }
            ],
        },
    )
    person_id = data["provenance"][0]["is_associated_with"][0]["person"]["id"]
    organization_id = data["provenance"][0]["is_associated_with"][0]["organization"]["id"]
    data = patch_dataset(
        {
            "actors": [
                {
                    "person": {"id": person_id},
                    "organization": {"id": organization_id},
                    "roles": ["creator"],
                },
            ]
        }
    )
    assert_nested_subdict(
        {
            "actors": [{**actor, "roles": ["creator"]}],
            "provenance": [{"description": {"en": "provenance"}, "is_associated_with": [actor]}],
        },
        data,
    )


def test_create_same_actor_twice_no_id(patch_dataset):
    person = {"name": "teppo", "email": "teppo@example.com"}
    org = {"pref_label": {"en": "test org"}, "email": "testorg@example.com"}
    data = patch_dataset(
        {
            "actors": [
                {"person": person, "organization": org, "roles": ["creator"]},
            ]
        }
    )
    actor_id = data["actors"][0]["id"]
    data = patch_dataset(
        {
            "actors": [  # role is allowed to change
                {"person": person, "organization": org, "roles": ["publisher"]},
            ]
        }
    )
    assert actor_id == data["actors"][0]["id"]


def test_create_same_person_twice_no_id(patch_dataset):
    person = {"name": "teppo", "email": "teppo@example.com"}
    org = {"pref_label": {"en": "test org"}, "email": "testorg@example.com"}
    data = patch_dataset(
        {
            "id": "#a",  # force new actor
            "actors": [
                {"person": person, "organization": org, "roles": ["creator"]},
            ],
        }
    )
    person_id = data["actors"][0]["person"]["id"]
    data = patch_dataset(
        {
            "id": "#a",  # force new actor
            "actors": [  # role is allowed to change
                {"person": person, "organization": org, "roles": ["publisher"]},
            ],
        }
    )
    assert person_id == data["actors"][0]["person"]["id"]


def test_create_same_organization_twice_no_id(patch_dataset):
    person = {"name": "teppo", "email": "teppo@example.com"}
    org = {"pref_label": {"en": "test org"}, "email": "testorg@example.com"}
    data = patch_dataset(
        {
            "id": "#a",  # force new actor
            "actors": [
                {"person": person, "organization": org, "roles": ["creator"]},
            ],
        }
    )
    organization_id = data["actors"][0]["organization"]["id"]
    data = patch_dataset(
        {
            "id": "#a",  # force new actor
            "actors": [  # role is allowed to change
                {"person": person, "organization": org, "roles": ["publisher"]},
            ],
        }
    )
    assert organization_id == data["actors"][0]["organization"]["id"]


def test_create_actor_email_private(patch_dataset, admin_client):
    """Actor email addresses should not be visible to users without editing rights to dataset."""
    data = patch_dataset(
        {
            "actors": [
                {
                    "person": {"name": "teppo", "email": "person@example.com"},
                    "organization": {"pref_label": {"en": "org"}, "email": "org@example.com"},
                    "roles": ["creator", "publisher"],
                }
            ]
        }
    )
    # Email should be visible when creating
    assert data["actors"][0]["person"]["email"] == "person@example.com"
    assert data["actors"][0]["organization"]["email"] == "org@example.com"

    res = admin_client.post(f"/v3/datasets/{data['id']}/publish", content_type="application/json")
    assert res.status_code == 200

    # Email should be visible on get if user has rights
    res = admin_client.get(f"/v3/datasets/{data['id']}", content_type="application/json")
    assert "email" in res.data["actors"][0]["person"]
    assert "email" in res.data["actors"][0]["organization"]

    # Email should not be visible for anonymous user
    anon_client = Client()
    res = anon_client.get(f"/v3/datasets/{data['id']}", content_type="application/json")
    assert "email" not in res.data["actors"][0]["person"]
    assert "email" not in res.data["actors"][0]["organization"]


def test_organization_depth_limit(
    admin_client, data_catalog, data_catalog_harvested, reference_data
):
    # Test adding organization with 3 levels
    org = {
        "pref_label": {"en": "level3"},
        "parent": {"pref_label": {"en": "level2"}, "parent": {"pref_label": {"en": "level1"}}},
    }
    dataset = {"title": {"en": "test"}, "actors": [{"roles": ["creator"], "organization": org}]}
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201

    # Add 4th level to organization
    org = {
        "pref_label": {"en": "level4"},
        "parent": org,
    }
    dataset = {"title": {"en": "test"}, "actors": [{"roles": ["creator"], "organization": org}]}
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert res.json() == {
        "actors": [
            {
                "organization": {
                    "parent": "Having more than 3 organization levels is not supported."
                }
            }
        ]
    }
