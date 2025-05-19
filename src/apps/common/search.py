import csv
import re
from typing import List

from watson.backends import RE_POSTGRES_ESCAPE_CHARS, PostgresSearchBackend, escape_query

re_space = re.compile("\s+")


def parse_search_string(string: str) -> List[str]:
    """Split search string while keeping doubly quoted parts together."""
    # Split e.g. 'hello "test dataset" -> ["hello", "test dataset"]
    reader = csv.reader([string], delimiter=" ", quotechar='"', escapechar="\\")
    parts = next(reader)
    # Replace remaining spaces with the 'followed by' operator <->
    return [re_space.sub("<->", part) for part in parts if part]


class CommonSearchBackend(PostgresSearchBackend):

    def escape_postgres_query(self, text):
        """Escapes the given text to become a valid ts_query."""
        # Modified to allow searching for exact phrases using double quotation marks
        q = " & ".join(
            "$${0}$$:*".format(word)
            for word in parse_search_string(escape_query(text, RE_POSTGRES_ESCAPE_CHARS))
        )
        return q
