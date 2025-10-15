import logging
import time
from collections import Counter

import pytest

from apps.common.profiling import count_queries, log_duration, log_queries
from apps.core import factories
from apps.core.models import Dataset, Provenance, Spatial


@pytest.mark.django_db
def test_count_queries():
    with count_queries() as counts:
        spatial = Spatial.objects.create(geographic_name="paikka")
        spatial.refresh_from_db()
        Provenance.objects.create(title={"en": "hello"}, spatial=spatial)
        Provenance.objects.create(title={"en": "world"})
        Provenance.objects.filter(title__en="hello").update(title={"fi": "moro"})
        Provenance.objects.all().delete()
    assert counts == {
        "SQLCompiler": Counter({"total": 1, "Spatial": 1}),
        "SQLInsertCompiler": Counter({"total": 3, "Provenance": 2, "Spatial": 1}),
        "SQLUpdateCompiler": Counter({"total": 4, "Provenance": 4}),
        "total": 8,
    }


@pytest.mark.django_db
def test_count_queries_log(caplog):
    logging.disable(logging.NOTSET)
    factories.DatasetFactory()
    with count_queries(log=True):
        Dataset.objects.count()
    assert len(caplog.messages) == 1
    assert "{'total': 1, 'SQLCompiler': Counter({'total': 1, 'Dataset': 1})}" in caplog.messages[0]


def test_log_duration():
    with log_duration() as times:
        time.sleep(0.01)
    assert times["duration"] >= 0.01


@pytest.mark.django_db
def test_log_queries(caplog):
    logging.disable(logging.NOTSET)
    factories.DatasetFactory(title={"en": "Hello world"})
    with log_queries():
        assert Dataset.objects.filter(title__en="Hello world").count() == 1
    assert len(caplog.messages) == 1
    msg = caplog.messages[0]
    assert "Execute SQL" in msg
    assert "Hello world" in msg


@pytest.mark.django_db
def test_log_queries_slow_limit(caplog):
    logging.disable(logging.NOTSET)
    factories.DatasetFactory(title={"en": "Hello world"})
    with log_queries(slow_limit=100):  # Query not logged if it takes <100 seconds
        assert Dataset.objects.filter(title__en="Hello world").count() == 1
    assert len(caplog.messages) == 0
