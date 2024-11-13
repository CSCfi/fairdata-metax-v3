import logging

import pytest
from django.db import transaction
from rest_framework import serializers

from apps.common.serializers import CommonModelSerializer
from apps.core.factories import DatasetFactory
from apps.core.models import AccessRights, Dataset
from apps.core.models.concepts import Spatial
from apps.core.serializers import DatasetSerializer, SpatialModelSerializer

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_nested_serializer_bulk_upsert(admin_user, location_reference_data, mocker):
    """Test that lazily saved nested model instances are upserted in bulk."""
    logging.disable(logging.NOTSET)
    dataset = DatasetFactory()

    # Normally Spatial list serializer does not support id data and only creates new spatials.
    # Make a dataset serializer class that accepts id for Spatial so we can verify that
    # bulk updating in deserialization works
    class SpatialModelSerializer2(SpatialModelSerializer):
        class Meta(SpatialModelSerializer.Meta):
            fields = SpatialModelSerializer.Meta.fields + ["id"]
            extra_kwargs = {"id": {"read_only": False, "required": False}}

    class DatasetSerializer2(DatasetSerializer):
        spatial = SpatialModelSerializer2(required=False, many=True, lazy=True)

    spatials = [
        {
            "geographic_name": "Alppikylä",
            "reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
        },
    ]

    create = mocker.spy(Spatial.objects, "create")
    bulk_create = mocker.spy(Spatial.objects, "bulk_create")

    class MockRequest:  # Mock required serializer context
        user = admin_user
        method = "PATCH"

        class View:
            query_params = {}

    # Updating dataset should create one spatial
    serializer = DatasetSerializer2(
        instance=dataset,
        data={"spatial": spatials},
        context={"request": MockRequest, "view": MockRequest.View},
        patch=True,
    )
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        dataset = serializer.save()

    assert Spatial.all_objects.count() == 1
    assert create.call_count == 0
    assert bulk_create.call_count == 1
    assert len(bulk_create.mock_calls[0].args[0]) == 1
    mocker.resetall()

    # Update the existing spatial name, add another spatial
    spatial_id = dataset.spatial.first().id
    spatials[0].update(
        {
            "id": spatial_id,
            "geographic_name": "Alppikylä is now Tapiola",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105747"},
        }
    )
    spatials.append(
        {
            "geographic_name": "Koitajoki",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105080"},
        }
    )

    # Updating dataset should update one spatial and create one spatial
    serializer = DatasetSerializer2(
        instance=dataset,
        data={"spatial": spatials},
        context={"request": MockRequest, "view": MockRequest.View},
        patch=True,
    )
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        dataset = serializer.save()
    dataset.refresh_from_db()  # Make sure we check dataset state in DB

    assert Spatial.all_objects.count() == 2
    assert create.call_count == 0
    assert bulk_create.call_count == 1  # Spatials were created/updated in one query
    assert len(bulk_create.mock_calls[0].args[0]) == 2
    spatial_1, spatial_2 = dataset.spatial.all()
    assert spatial_1.id == spatial_id  # Existing object was updated
    assert spatial_1.geographic_name == "Alppikylä is now Tapiola"
    assert spatial_1.reference.pref_label["fi"] == "Tapiola (Espoo)"
    assert spatial_2.geographic_name == "Koitajoki"
    assert spatial_2.reference.pref_label["fi"] == "Koitajoki"


@pytest.mark.django_db(transaction=True)
def test_nested_serializer_lazy_transaction_warning(
    caplog, admin_user, location_reference_data, mocker
):
    """Test that lazily saved nested model instances are upserted in bulk."""
    logging.disable(logging.NOTSET)
    dataset = DatasetFactory()

    class MockRequest:  # Mock required serializer context
        user = admin_user
        method = "PATCH"

        class View:
            query_params = {}

    # Updating dataset should create one spatial
    serializer = DatasetSerializer(
        instance=dataset,
        data={},
        context={"request": MockRequest, "view": MockRequest.View},
        patch=True,
    )
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        serializer.save()
    assert caplog.messages == []

    serializer.save()
    assert caplog.messages == [
        "DatasetSerializer has lazy serializer fields (provenance, spatial, temporal) and should update in a transaction."
    ]


def test_nested_serializer_strict():
    class B(CommonModelSerializer):
        class Meta:
            model = AccessRights
            fields = ["description"]

    class A(CommonModelSerializer):
        access_rights = B()

        class Meta:
            model = Dataset
            fields = ["access_rights"]

    # Default to strict serializer
    serializer = A(
        data={"access_rights": {"fielddoesnotexist": "nope", "description": {"en": "Hello"}}}
    )
    with pytest.raises(serializers.ValidationError) as ec:
        serializer.is_valid(raise_exception=True)
    assert str(ec.value.detail["access_rights"]["fielddoesnotexist"][0]) == "Unexpected field"

    # Allow non-strict serializer by setting strict=False in context
    serializer = A(
        data={"access_rights": {"fielddoesnotexist": "nope", "description": {"en": "Hello"}}},
        context={"strict": False},
    )
    assert serializer.is_valid() is True
