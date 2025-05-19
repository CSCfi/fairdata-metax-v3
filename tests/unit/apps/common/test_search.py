from apps.common.search import CommonSearchBackend


def test_escape_postgres_query():
    backend = CommonSearchBackend()
    escaped = backend.escape_postgres_query("Kubrick, 2022: A Space Odyssey")
    assert escaped == "$$Kubrick,$$:* & $$2022$$:* & $$A$$:* & $$Space$$:* & $$Odyssey$$:*"

    # Phrases in quotation marks expect words in specific order
    escaped = backend.escape_postgres_query('"Kubrick, 2022: A Space Odyssey"')
    assert escaped == "$$Kubrick,<->2022<->A<->Space<->Odyssey$$:*"
