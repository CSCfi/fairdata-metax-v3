import contextlib
import pytest
from rest_framework.serializers import ValidationError

from apps.core import factories
from apps.core.serializers import DatasetSerializer


pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.mark.parametrize(
    "allowed_pid_types,generate_pid_on_publish,persistent_identifier,error",
    [
        (["external"], None, None, "has to have a persistent identifier"),
        (["external"], None, "external-pid", None),
        (["external"], "URN", None, "catalog does not allow PID generation"),
        (["external"], "URN", "external-pid", "using generate_pid_on_publish"),
        (["URN"], None, None, "Value is required by the catalog when publishing"),
        (["URN"], "URN", None, None),
        (["URN"], "DOI", None, "is not a valid choice for catalog"),
        (["URN"], "DOI", "external-pid", "using generate_pid_on_publish"),
        (["URN", "DOI"], "DOI", None, None),
        (["URN"], None, "external-pid", "user-defined PID is not supported by the catalog"),
        (["URN", "external"], "URN", None, None),
        (["URN", "external"], None, "external-pid", None),
        (["URN", "external"], "URN", "external-pid", "using generate_pid_on_publish"),
    ],
)
def test_dataset_allowed_pid_types(
    allowed_pid_types, generate_pid_on_publish, persistent_identifier, error
):
    """The data catalog determines which PID types are supported."""
    catalog = factories.DataCatalogFactory(allowed_pid_types=allowed_pid_types)
    dataset = factories.DatasetFactory(data_catalog=catalog)
    dataset.actors.set([factories.DatasetActorFactory(roles=["creator", "publisher"])])
    dataset.generate_pid_on_publish = generate_pid_on_publish

    exc = None
    with contextlib.ExitStack() as stack:
        if error:
            exc = stack.enter_context(pytest.raises(ValidationError))
        DatasetSerializer.validate_new_pid(dataset=dataset, new_pid=persistent_identifier)
        dataset.persistent_identifier = persistent_identifier
        dataset.save()
        dataset.publish()
    if error:
        assert error in str(exc.value)


@pytest.mark.parametrize(
    "allowed_pid_types,pid_generated_by_fairdata,persistent_identifier,error",
    [
        (["external"], False, "new-pid", None),
        (["external"], False, None, "Dataset has to have a persistent identifier when publishing"),
        (["external"], True, "new-pid", "Changing generated PID is not allowed"),
        (["URN", "external"], False, "new-pid", None),
        (["URN", "external"], True, "new-pid", "Changing generated PID is not allowed"),
        (["URN"], False, "new-pid", "user-defined PID is not supported by the catalog"),
        (["URN"], True, "new-pid", "Changing generated PID is not allowed"),
    ],
)
def test_dataset_pid_changes(
    allowed_pid_types, pid_generated_by_fairdata, persistent_identifier, error
):
    """Changing PID is allowed only if it's supported by catalog and old PID is not generated."""
    catalog = factories.DataCatalogFactory(allowed_pid_types=allowed_pid_types)
    dataset = factories.DatasetFactory(data_catalog=catalog, persistent_identifier="old-pid")
    dataset.actors.set([factories.DatasetActorFactory(roles=["creator", "publisher"])])
    dataset.pid_generated_by_fairdata = pid_generated_by_fairdata
    dataset.save()
    dataset.publish()

    exc = None
    with contextlib.ExitStack() as stack:
        if error:
            exc = stack.enter_context(pytest.raises(ValidationError))
        DatasetSerializer.validate_new_pid(
            dataset=dataset,
            new_pid=persistent_identifier,
        )
        dataset.persistent_identifier = persistent_identifier
        dataset.save()
    if error:
        assert error in str(exc.value)


def test_dataset_pid_with_no_catalog():
    """Cannot assign PID without a catalog."""
    with pytest.raises(ValidationError) as exc:
        factories.DatasetFactory(data_catalog=None, persistent_identifier="pid-here")
    assert "Can't assign persistent_identifier if data_catalog isn't given." in str(exc.value)


def test_dataset_create_pid_with_draft():
    """Cannot assign PID without a catalog."""
    dataset = factories.DatasetFactory(persistent_identifier=None)
    with pytest.raises(ValueError) as exc:
        dataset.create_persistent_identifier()
    assert "Dataset is a draft" in str(exc.value)


def test_dataset_create_pid_with_existing():
    """Cannot assign PID without a catalog."""
    dataset = factories.PublishedDatasetFactory(persistent_identifier="pid-here")
    with pytest.raises(ValueError) as exc:
        dataset.create_persistent_identifier()
    assert "Dataset already has a PID" in str(exc.value)


def test_dataset_create_pid_unknown_type():
    """Try use create_persistent_identifier with a PID type it cannot handle."""
    catalog = factories.DataCatalogFactory(allowed_pid_types=["fake"])
    dataset = factories.DatasetFactory(
        persistent_identifier=None, generate_pid_on_publish="fake", data_catalog=catalog
    )
    dataset.state = "published"
    with pytest.raises(ValueError) as exc:
        dataset.create_persistent_identifier()
    assert "Unknown PID type 'fake'" in str(exc.value)
