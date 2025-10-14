import pytest

from apps.core import factories


@pytest.mark.parametrize(
    "start_date,end_date,count",
    [
        ("2023-07-01", "2023-07-01", 1),  # Single date within temporal
        ("2022-07-01", "2022-07-01", 0),  # Single date before temporal
        ("2024-07-01", "2024-07-01", 0),  # Single date after temporal
        ("2023-01-01", "2023-12-31", 1),  # Exact match of temporal
        ("2023-02-01", "2023-11-30", 1),  # Time range completely within temporal
        ("2022-01-01", "2024-12-31", 1),  # Time range that covers completely temporal
        ("2023-02-01", "2024-11-30", 1),  # Time range that starts within temporal
        ("2022-02-01", "2023-11-30", 1),  # Time range that ends within temporal
        ("2022-01-01", "2022-12-31", 0),  # Time range completely before temporal
        ("2024-01-01", "2024-12-31", 0),  # Time range completely after temporal
    ],
)
def test_temporal_filter_start_given_end_given(
    admin_client,
    start_date,
    end_date,
    count,
):
    factories.DatasetFactory(
        temporal=[factories.TemporalFactory(start_date="2023-01-01", end_date="2023-12-31")]
    )

    res = admin_client.get(
        f"/v3/datasets?temporal__start_date={start_date}&temporal__end_date={end_date}"
    )
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "start_date,end_date,count",
    [
        ("2023-07-01", "2023-07-01", 1),  # Single date after start date
        ("2022-07-01", "2022-07-01", 0),  # Single date before start date
        ("2023-01-01", "2023-01-01", 1),  # Exact match of start date
        ("2023-02-01", "2023-11-30", 1),  # Time range that starts after start date
        ("2022-02-01", "2023-11-30", 1),  # Time range that ends after start date
        ("2022-01-01", "2022-12-31", 0),  # Time range completely before start date
    ],
)
def test_temporal_filter_start_given_end_not_given(
    admin_client,
    start_date,
    end_date,
    count,
):
    factories.DatasetFactory(
        temporal=[factories.TemporalFactory(start_date="2023-01-01", end_date=None)]
    )

    res = admin_client.get(
        f"/v3/datasets?temporal__start_date={start_date}&temporal__end_date={end_date}"
    )
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "start_date,end_date,count",
    [
        ("2024-07-01", "2024-07-01", 0),  # Single date after end date
        ("2022-07-01", "2022-07-01", 1),  # Single date before start date
        ("2023-12-31", "2023-12-31", 1),  # Exact match of end date
        ("2024-02-01", "2024-11-30", 0),  # Time range that starts after end date
        ("2022-02-01", "2023-11-30", 1),  # Time range that ends before end date
        ("2022-02-01", "2024-11-30", 1),  # Time range that starts before end date
    ],
)
def test_temporal_filter_start_not_given_end_given(
    admin_client,
    start_date,
    end_date,
    count,
):
    factories.DatasetFactory(
        temporal=[factories.TemporalFactory(start_date=None, end_date="2023-12-31")]
    )

    res = admin_client.get(
        f"/v3/datasets?temporal__start_date={start_date}&temporal__end_date={end_date}"
    )
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "start_date,end_date,count",
    [
        ("2024-07-01", "2024-07-01", 0),  # Single date
        ("2024-01-01", "2024-12-31", 0),  # Time range
    ],
)
def test_temporal_filter_start_not_given_end_not_given(
    admin_client,
    start_date,
    end_date,
    count,
):
    factories.DatasetFactory(temporal=[factories.TemporalFactory(start_date=None, end_date=None)])

    res = admin_client.get(
        f"/v3/datasets?temporal__start_date={start_date}&temporal__end_date={end_date}"
    )
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "start_date,end_date,count",
    [
        ("2022-07-01", "2022-07-01", 0),  # Single date before temporals
        ("2023-07-01", "2023-07-01", 1),  # Single date within first temporal
        ("2024-07-01", "2024-07-01", 0),  # Single date between temporals
        ("2025-07-01", "2025-07-01", 1),  # Single date within second temporal
        ("2026-07-01", "2026-07-01", 0),  # Single date after temporals
        ("2022-01-01", "2026-12-31", 1),  # Time range that covers completely both temporals
        ("2022-01-01", "2024-12-31", 1),  # Time range that covers completely first temporal
        ("2024-01-01", "2026-12-31", 1),  # Time range that covers completely second temporal
        ("2022-01-01", "2022-12-31", 0),  # Time range completely before temporals
        ("2024-01-01", "2024-12-31", 0),  # Time range completely between temporals
        ("2026-01-01", "2026-12-31", 0),  # Time range completely after temporals
        ("2022-02-01", "2023-11-30", 1),  # Time range that covers partially the first temporal
        ("2025-02-01", "2026-11-30", 1),  # Time range that covers partially the second temporal
    ],
)
def test_temporal_filter_multiple_temporals(
    admin_client,
    start_date,
    end_date,
    count,
):
    factories.DatasetFactory(
        temporal=[
            factories.TemporalFactory(start_date="2023-01-01", end_date="2023-12-31"),
            factories.TemporalFactory(start_date="2025-01-01", end_date="2025-12-31"),
        ]
    )

    res = admin_client.get(
        f"/v3/datasets?temporal__start_date={start_date}&temporal__end_date={end_date}"
    )
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "temporal_start_date,temporal_end_date,count",
    [
        ("2025-01-01", "2025-12-31", 1),  # Time range starting from search date
        ("2025-02-01", "2025-12-31", 1),  # Time range starting after search date
        ("2024-01-01", "2024-12-31", 0),  # Time range ending before search date
        ("2024-12-31", "2025-12-31", 1),  # Time range starting before search date
        ("2025-01-01", None, 1),  # Time range starting from search date, without end date
        ("2025-02-01", None, 1),  # Time range starting after search date, without end date
        ("2024-01-01", None, 1),  # Time range starting before search date, without end date
        (None, "2025-01-01", 1),  # Time range ending to search date, without start date
        (None, "2024-01-01", 0),  # Time range ending before search date, without start date
        (None, "2025-02-01", 1),  # Time range ending after search date, without start date
    ],
)
def test_temporal_filter_end_param_not_given(
    admin_client,
    temporal_start_date,
    temporal_end_date,
    count,
):
    factories.DatasetFactory(
        temporal=[
            factories.TemporalFactory(start_date=temporal_start_date, end_date=temporal_end_date)
        ]
    )

    res = admin_client.get(f"/v3/datasets?temporal__start_date=2025-01-01")
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "temporal_start_date,temporal_end_date,count",
    [
        ("2025-01-01", "2025-12-31", 1),  # Time range ending on search date
        ("2025-01-01", "2026-12-31", 1),  # Time range ending after search date
        ("2024-01-01", "2024-12-31", 1),  # Time range ending before search date
        ("2025-01-01", None, 1),  # Time range starting before search date, without end date
        ("2026-01-01", None, 0),  # Time range starting after search date, without end date
        (None, "2025-12-31", 1),  # Time range ending to search date, without start date
        (None, "2025-01-01", 1),  # Time range ending before search date, without start date
        (None, "2026-01-01", 1),  # Time range ending after search date, without start date
    ],
)
def test_temporal_filter_start_param_not_given(
    admin_client,
    temporal_start_date,
    temporal_end_date,
    count,
):
    factories.DatasetFactory(
        temporal=[
            factories.TemporalFactory(start_date=temporal_start_date, end_date=temporal_end_date)
        ]
    )

    res = admin_client.get(f"/v3/datasets?temporal__end_date=2025-12-31")
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "start_date,end_date,error_message",
    [
        (
            "foo",
            "2024-01-01",
            {"temporal__start_date": ["Enter a valid date."]},
        ),
        (
            "2024-01-01",
            "foo",
            {"temporal__end_date": ["Enter a valid date."]},
        ),
        (
            "2024-01-01",
            "2023-01-01",
            {"temporal__end_date": "temporal__end_date must not be before temporal__start_date"},
        ),
    ],
)
def test_temporal_filter_invalid_params(
    admin_client,
    start_date,
    end_date,
    error_message,
):
    res = admin_client.get(
        f"/v3/datasets?temporal__start_date={start_date}&temporal__end_date={end_date}"
    )
    assert res.status_code == 400
    assert res.json() == error_message


@pytest.mark.parametrize(
    "start_date,end_date,count",
    [
        ("2023-07-01", "2024-07-01", 0),
        ("2023-07-01", None, 0),
        (None, "2024-07-01", 0),
        (None, None, 1),
    ],
)
def test_temporal_filter_with_only_temporal_coverage(admin_client, start_date, end_date, count):
    factories.DatasetFactory(
        temporal=[
            factories.TemporalFactory(
                start_date=None, end_date=None, temporal_coverage="some time interval"
            )
        ]
    )
    query = {}
    if start_date:
        query["temporal__start_date"] = start_date
    if end_date:
        query["temporal__end_date"] = end_date
    res = admin_client.get("/v3/datasets", data=query)
    assert res.status_code == 200, res.data
    assert res.data["count"] == count
