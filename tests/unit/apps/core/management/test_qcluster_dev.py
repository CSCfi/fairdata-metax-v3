import pytest
from django.core.management import call_command


from unittest.mock import patch, MagicMock

pytestmark = [
    pytest.mark.management,
]


def test_qcluster_dev():
    # Patch run_with_reloader and the qcluster handler
    # to avoid actually running the qcluster
    with patch(
        "django.utils.autoreload.run_with_reloader", lambda f, *args, **kwargs: f(*args, **kwargs)
    ), patch("django_q.management.commands.qcluster.Command.handle", MagicMock()):
        call_command("qcluster_dev")
