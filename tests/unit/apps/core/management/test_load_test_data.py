from io import StringIO

import pytest
from django.core.management import call_command

@pytest.mark.django_db
def test_loading_test_data():
    out = StringIO()
    call_command("load_test_data", stdout=out, stderr=StringIO())
    assert out.getvalue().strip() == "test objects created successfully"
