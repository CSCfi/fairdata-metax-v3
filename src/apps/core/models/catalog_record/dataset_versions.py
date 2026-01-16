import logging

from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import Case, Count, F, OuterRef, Value, When, Q
from django.db.models.functions import Coalesce

from apps.common.models import AbstractBaseModel

logger = logging.getLogger(__name__)


@transaction.atomic
def update_dataset_versions_order(queryset) -> int:
    """Recalculate datasets_versions_order field for datasets in queryset.

    Within each DatasetVersions, independent dataset versions
    (i.e. dataset.draft_of=None) are assigned an even number
    and the next_draft of each version gets the next odd number.

    Assumes that creation timestamps of the independent versions correspond to the
    actual creation order. Creation timestamps of the change draft datasets do not
    affect the order.

    Returns:
        int: Number of changed update_dataset_ordering values.
    """

    queryset = queryset.order_by().annotate(
        # Use original version creation timestamp for change drafts
        version_created=Coalesce("draft_of__created", "created"),
        # Count how many older datasets are in the same DatasetVersions
        older_version_count=Count(
            "dataset_versions__datasets",
            filter=Q(
                dataset_versions__datasets__draft_of__isnull=True,
                dataset_versions__datasets__created__lt=F("version_created"),
            ),
        ),
        new_order=Case(
            When(draft_of__isnull=True, then=F("older_version_count") * 2),
            When(draft_of__isnull=False, then=F("older_version_count") * 2 + 1),
        ),
    )

    # Get only changed values
    updates = queryset.exclude(dataset_versions_order=F("new_order")).values_list(
        "id", "new_order"
    )

    # Update values in separate query because Django does
    # not like joins (e.g. draft_of__created) in an update.
    update_ids = []  # Ids of datasets that should be updated
    cases = []
    for dataset_id, order in updates:
        update_ids.append(dataset_id)
        if order != 0:  # Use 0 as default to reduce number of cases
            cases.append(When(id=dataset_id, then=Value(order)))

    # Temporarily clear existing values to prevent uniqueness violations during update
    queryset.filter(id__in=update_ids, dataset_versions_order__isnull=False).update(
        dataset_versions_order=None
    )

    # Do the actual update
    update_count = queryset.filter(id__in=update_ids).update(
        dataset_versions_order=Case(*cases, default=Value(0))
    )
    return update_count


class DatasetVersions(AbstractBaseModel):
    """A collection of dataset's versions."""

    # List of ids of legacy datasets belonging to set. May contain ids
    # of datasets that haven't been migrated yet.
    legacy_versions = ArrayField(models.UUIDField(), default=list, blank=True)

    def update_dataset_order(self) -> int:
        """Recalculate datasets_versions_order field of associated datasets."""
        datasets = self.datasets(manager="all_objects")
        return update_dataset_versions_order(queryset=datasets)
