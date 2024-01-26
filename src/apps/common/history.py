from simple_history.models import HistoricalRecords


class SnapshotHistoricalRecords(HistoricalRecords):
    """Historical records with explicit snapshotting.

    Normal HistoricalRecords automatically creates a historical record
    on post_save and m2m_changed signals. This has several disadvantages:
    - When instance is created, the first record does not have reverse relations
    - Each m2m update produces an extra record
    - Changes in reversely related models don't trigger

    This class adds a `create_snapshot` method to the model
    that has to be explicitly called when a historical record is desired.
    """

    def add_extra_methods(self, cls):
        super().add_extra_methods(cls)
        history = self

        def create_snapshot(self, created=False, *args, **kwargs):
            """Create a historical snapshot of model.

            Does not save the model.
            """
            history.create_historical_record(self, created and "+" or "~")

        setattr(cls, "create_snapshot", create_snapshot)

    def post_save(self, instance, created, using=None, **kwargs):
        """Signal handling disable for post_save."""

    def m2m_changed(self, instance, action, attr, pk_set, reverse, **_):
        """Signal handling disabled for m2m_changed."""
