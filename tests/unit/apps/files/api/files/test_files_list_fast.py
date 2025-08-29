import pytest

from apps.common.profiling import count_queries
from apps.files.views.file_view import FileViewSet

pytestmark = [pytest.mark.django_db, pytest.mark.file]


# Fields that can be rendered using the fast path
# which doesn't use model instances.
# Listed explicitly here to ensure tests have to be
# updated when new fast fields are added.
fast_fields = [
    "characteristics_extension",
    "checksum",
    "csc_project",
    "filename",
    "frozen",
    "id",
    "modified",
    "pas_process_running",
    "pathname",
    "published",
    "removed",
    "size",
    "storage_identifier",
    "storage_service",
    "user",
]


def test_files_fast_fields():
    """The fast_fields list should include all fast fields from the view."""
    assert set(fast_fields) == FileViewSet.get_fast_fields()


@pytest.mark.parametrize("include_nulls", [False, True])
def test_files_list_fast(admin_client, file_tree_a, include_nulls):
    """Test files list fast path."""
    params = {
        **file_tree_a["params"],
        "fields": ",".join(fast_fields),
        "pagination": False,
        "include_nulls": include_nulls,
    }

    with count_queries() as count:
        res = admin_client.get(
            "/v3/files",
            params,
            content_type="application/json",
        )
    # Confirm FileStorage was not fetched in a separate query (we're in the fast path)
    assert "FileStorage" not in count["SQLCompiler"]

    results = res.json()
    assert len(results) == 16
    assert results[0]["pathname"] == "/rootfile.txt"
    assert results[1]["pathname"] == "/dir/a.txt"

    # Check that the fast path produces the same results as the slow path.
    # The response should be identical except for the slow extra field.
    params["fields"] += ",characteristics"
    with count_queries() as count:
        res_slow = admin_client.get(
            "/v3/files",
            params,
            content_type="application/json",
        )
    # Confirm FileStorage was fetched in a separate query (we're in the slow path)
    assert "FileStorage" in count["SQLCompiler"]

    results_slow = res_slow.json()
    assert len(results_slow) == 16
    assert results_slow[0]["pathname"] == "/rootfile.txt"
    results_slow[0].pop("characteristics", None)

    # Fields should have the same values and be in the same order in both paths
    fast_items = list(results[0].items())
    slow_items = list(results_slow[0].items())
    assert len(slow_items) == len(fast_items)
    for fast_item, slow_item in zip(fast_items, slow_items):
        assert fast_item == slow_item
