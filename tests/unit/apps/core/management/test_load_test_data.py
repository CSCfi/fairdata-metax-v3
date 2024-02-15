import logging
from io import StringIO

import pytest
from django.core.management import call_command

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_loading_test_data(caplog, reference_data):
    logging.disable(logging.NOTSET)  # "undisable" logging disabled in tweaked_settings fixture
    out = StringIO()
    call_command("load_test_data", stdout=out, stderr=StringIO())

    # Ensure there were no errors logged
    errors = [record.message for record in caplog.records if record.levelno >= logging.ERROR]
    assert errors == []

    assert "test objects created successfully" in out.getvalue().strip()
    assert "test catalogs created successfully" in out.getvalue().strip()
