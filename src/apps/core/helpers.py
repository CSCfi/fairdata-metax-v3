import re

from apps.core.models.catalog_record import Dataset


def get_metax_identifiers_by_pid(identifier, context={}):
    pid = clean_pid(identifier)
    if (pid_map := context.get("datasets_by_pid")) is not None:
        return pid_map.get(pid, [])
    return list(
        Dataset.available_objects.filter(
            persistent_identifier=pid, state=Dataset.StateChoices.PUBLISHED
        ).values_list("id", flat=True)
    )


def clean_pid(pid_string):
    doi_replaced = re.sub("^https://doi.org/", "doi:", pid_string)
    urn_removed = re.sub("^http://urn.fi/", "", doi_replaced)
    return urn_removed
