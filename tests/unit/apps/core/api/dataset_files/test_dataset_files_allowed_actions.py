"""Tests for updating dataset files with /dataset/<id>/files endpoint."""

import pytest

from apps.core import factories
from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def do_action(data_catalog, admin_client, deep_file_tree):
    def _do(
        state,
        has_files,
        action=None,
        cumulative_state=Dataset.CumulativeState.NOT_CUMULATIVE,
        patch_fields={},
    ):
        if state == "published" or state == "draft_of":
            dataset = factories.PublishedDatasetFactory(
                data_catalog=data_catalog, cumulative_state=cumulative_state
            )
        elif state == "draft":
            dataset = factories.DatasetFactory(
                data_catalog=data_catalog, cumulative_state=cumulative_state
            )

        if has_files:
            initial_actions = {
                **deep_file_tree["params"],
                "directory_actions": [{"pathname": "/dir1/"}],
            }
            res = admin_client.patch(
                f"/v3/datasets/{dataset.id}",
                {"fileset": initial_actions},
                content_type="application/json",
            )
            assert res.status_code == 200
            dataset.refresh_from_db()

        if state == "draft_of":
            dataset = dataset.create_new_draft()

        if action:
            actions = {
                **deep_file_tree["params"],
                "directory_actions": [
                    {"pathname": "/dir1/", "action": action},
                    {"pathname": "/dir2/", "action": action},
                ],
            }
            res = admin_client.patch(
                f"/v3/datasets/{dataset.id}",
                {"fileset": actions, **patch_fields},
                content_type="application/json",
            )
        else:
            res = admin_client.patch(
                f"/v3/datasets/{dataset.id}",
                patch_fields,
                content_type="application/json",
            )
        return res

    return _do


def test_add_files_to_empty_published_dataset(do_action):
    res = do_action(state="published", has_files=False, action="add")
    assert res.status_code == 200


def test_add_files_to_published_dataset_with_files(do_action):
    res = do_action(state="published", has_files=True, action="add")
    assert res.status_code == 400
    assert (
        res.json()["fileset"]["action"]
        == "Adding files to a published noncumulative dataset is not allowed."
    )


def test_add_files_to_draft_of_empty_published_dataset(do_action):
    res = do_action(state="draft_of", has_files=False, action="add")
    assert res.status_code == 200


def test_add_files_to_draft_of_published_dataset_with_files(do_action):
    res = do_action(state="draft_of", has_files=True, action="add")
    assert res.status_code == 400
    assert (
        res.json()["fileset"]["action"]
        == "Adding files to a published noncumulative dataset is not allowed."
    )


def test_add_files_to_cumulative_dataset(do_action):
    res = do_action(
        state="published",
        has_files=True,
        action="add",
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.ACTIVE


def test_add_files_to_cumulative_dataset_and_close(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="published",
        has_files=True,
        action="add",
        cumulative_state=Dataset.CumulativeState.ACTIVE,
        patch_fields={"cumulative_state": Dataset.CumulativeState.CLOSED},
    )
    assert res.status_code == 200

    # Check dataset is closed
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"fileset": {**deep_file_tree["params"], "directory_actions": [{"pathname": "/"}]}},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert (
        res.json()["fileset"]["action"]
        == "Adding files to a published noncumulative dataset is not allowed."
    )


def test_change_published_dataset_cumulative(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="published",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.NOT_CUMULATIVE,
        patch_fields={"cumulative_state": Dataset.CumulativeState.ACTIVE},
    )
    # Dataset already published, cannot make it cumulative afterwards
    assert res.status_code == 400
    assert res.json()["cumulative_state"] == "Cannot change state to 1."


def test_add_files_to_cumulative_dataset_and_exclude_some(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="published",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )

    # Allow "remove" if it excludes files being added and does not remove any existing
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {
            "fileset": {
                **deep_file_tree["params"],
                "directory_actions": [{"pathname": "/dir3/"}],
                "file_actions": [{"pathname": "/dir3/sub1/file.txt", "action": "remove"}],
            }
        },
        content_type="application/json",
    )
    assert res.status_code == 200


# Remove files


def test_remove_files_from_draft_dataset(do_action):
    res = do_action(
        state="draft",
        has_files=True,
        action="remove",
    )
    assert res.status_code == 200


def test_remove_files_from_cumulative_draft_dataset(do_action):
    res = do_action(
        state="draft",
        has_files=True,
        action="remove",
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200


def test_remove_files_from_published_dataset_with_files(do_action):
    res = do_action(
        state="published",
        has_files=True,
        action="remove",
    )
    assert res.status_code == 400
    assert (
        res.json()["fileset"]["action"]
        == "Removing files from a published dataset is not allowed."
    )


def test_remove_files_from_cumulative_dataset(do_action):
    res = do_action(
        state="published",
        has_files=True,
        action="remove",
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 400
    assert (
        res.json()["fileset"]["action"]
        == "Removing files from a published dataset is not allowed."
    )


# Draft merge


def test_merge_file_addition_to_cumulative_dataset(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="draft_of",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.ACTIVE

    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {
            "cumulative_state": Dataset.CumulativeState.CLOSED,
            "fileset": {**deep_file_tree["params"], "directory_actions": [{"pathname": "/"}]},
        },
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/publish?include_nulls=true",
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.CLOSED
    assert res.data["next_draft"] is None


def test_file_addition_original_is_closed(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="draft_of",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.ACTIVE

    # Close original
    close_res = admin_client.patch(
        f"/v3/datasets/{res.data['draft_of']['id']}",
        {"cumulative_state": Dataset.CumulativeState.CLOSED},
        content_type="application/json",
    )
    assert close_res.status_code == 200

    # Closed original should prevent adding files to draft
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {
            "cumulative_state": Dataset.CumulativeState.CLOSED,
            "fileset": {**deep_file_tree["params"], "directory_actions": [{"pathname": "/"}]},
        },
        content_type="application/json",
    )
    assert res.status_code == 400
    assert (
        res.json()["fileset"]["action"]
        == "Adding files to a published noncumulative dataset is not allowed."
    )


def test_merge_file_addition_to_closed_dataset(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="draft_of",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.ACTIVE

    # Add files while original is not yet closed
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {
            "fileset": {**deep_file_tree["params"], "directory_actions": [{"pathname": "/"}]},
        },
        content_type="application/json",
    )
    assert res.status_code == 200

    # Close original
    close_res = admin_client.patch(
        f"/v3/datasets/{res.data['draft_of']['id']}",
        {"cumulative_state": Dataset.CumulativeState.CLOSED},
        content_type="application/json",
    )
    assert close_res.status_code == 200

    # Incompatible draft, merge should be prevented
    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/publish",
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json()["fileset"] == "Merging changes would add files, which is not allowed."


def test_merge_file_removal(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="draft_of",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.ACTIVE

    # Add files to original
    orig_res = admin_client.patch(
        f"/v3/datasets/{res.data['draft_of']['id']}",
        {
            "cumulative_state": Dataset.CumulativeState.CLOSED,
            "fileset": {**deep_file_tree["params"], "directory_actions": [{"pathname": "/"}]},
        },
        content_type="application/json",
    )
    assert orig_res.status_code == 200

    # Files added to original are missing from draft, so merge would remove them
    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/publish",
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json()["fileset"] == "Merging changes would remove files, which is not allowed."


def test_merge_close(do_action, admin_client, deep_file_tree):
    res = do_action(
        state="draft_of",
        has_files=True,
        cumulative_state=Dataset.CumulativeState.ACTIVE,
    )
    assert res.status_code == 200
    assert res.data["cumulative_state"] == Dataset.CumulativeState.ACTIVE
    assert res.data["fileset"] is not None

    # Set draft to close cumulation
    orig_res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {
            "cumulative_state": Dataset.CumulativeState.CLOSED,
        },
        content_type="application/json",
    )
    assert orig_res.status_code == 200
    assert res.data["fileset"] is not None

    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/publish",
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["fileset"] is not None
