from django.db.models import Func


class SplitPart(Func):
    """PostgreSQL function split_part(string text, delimiter text, field int)

    Split string on delimiter and return the given field (counting from one)
    """

    function = "SPLIT_PART"
    arity = 3
