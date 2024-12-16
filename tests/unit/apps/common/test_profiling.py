import logging
import time
from collections import Counter

from apps.common.profiling import count_queries, log_duration
from apps.core import factories
from apps.core.models import Dataset, Provenance, Spatial


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
