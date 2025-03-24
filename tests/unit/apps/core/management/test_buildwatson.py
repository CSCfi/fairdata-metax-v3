import pytest
from apps.core import factories
from apps.core.models import Dataset
from django.core.management import call_command
from watson.search import filter, skip_index_update
from watson.models import SearchEntry


@pytest.mark.django_db()
def test_buildwatson():
    """Test customized buildwatson command in case it breaks in a future django-watson update."""
    with skip_index_update():
        factories.PublishedDatasetFactory(title={"en": "hello world"})
        factories.PublishedDatasetFactory(title={"en": "hello metax user"})
    assert SearchEntry.objects.count() == 0

    call_command("buildwatson")
    qs = filter(queryset=Dataset.objects.all(), search_text="hello")
    assert qs.count() == 2
