from contextlib import contextmanager
import logging
import multiprocessing
from unittest.mock import patch

from django.utils import autoreload
from django_q.management.commands import qcluster

logger = logging.getLogger(__name__)


class Command(qcluster.Command):
    """Minimal wrapper around qcluster with autoreload."""

    help = "Starts a development Django Q Cluster with autoreload on code changes."

    def __init__(self, *args, **kwargs):
        self.process = None
        super().__init__(*args, **kwargs)

    @contextmanager
    def patch_qcluster(self):
        """Patch autoreload.trigger_reload so it stops the qcluster process."""
        _trigger_reload = autoreload.trigger_reload

        def trigger_reload(filename):
            if self.process:
                self.process.terminate()
            _trigger_reload(filename)

        with patch("django.utils.autoreload.trigger_reload", trigger_reload):
            yield

    def run_qcluster(self, *args, **options):
        """Run the original qcluster handler in separate process."""
        with self.patch_qcluster():
            # Qcluster needs to be run in a seperate process because
            # it uses OS signals which is not supported with run_with_reloader.
            self.process = multiprocessing.Process(
                target=super().handle, args=args, kwargs=options
            )
            self.process.start()
            self.process.join()  # Wait for process to terminate

    def handle(self, *args, **options):
        autoreload.run_with_reloader(self.run_qcluster, *args, **options)
