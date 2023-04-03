from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_update_default_essentials():
    out = StringIO()
    call_command("update_default_essential_choices", stdout=out, stderr=StringIO())
    assert out.getvalue().strip() == "default essentials updated successfully"
