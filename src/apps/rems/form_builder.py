from enum import StrEnum
import logging

from apps.common.helpers import flatten_dict, single_translation

logger = logging.getLogger(__name__)


class REMSField:
    field_type: str

    def __init__(self, field_id: str, title: dict, optional=False):
        # Field id is internal to the form, so the same value can be used in multiple forms.
        self.field_id = field_id
        self.title = title
        self.optional = optional

    @property
    def data(self) -> dict:
        data = {
            "field/id": self.field_id,
            "field/title": self.title,
            "field/type": self.field_type,
            "field/optional": self.optional,
        }

        return data


class REMSTextField(REMSField):
    field_type = "text"

    def __init__(self, *args, max_length: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_length = max_length

    @property
    def data(self) -> dict:
        return {**super().data, "field/max-length": self.max_length}


class FormKeys(StrEnum):
    """Keys for the form data dict."""

    ORGANIZATION = "organization"
    FIELDS = "form/fields"

    # Form name shown in the REMS admin UI
    INTERNAL_NAME = "form/internal-name"
    # Translated form title shown to applicants when using the REMS UI
    EXTERNAL_TITLE = "form/external-title"
    # There's also form/title which is deprecated and should not be used.
    # When form/title is used, it also replaces values of internal-name and external-title.


class REMSFormBuilder:
    def __init__(self, organization: dict, title: dict, fields=None):
        self.organization = organization
        self.title = title
        self.fields: list[REMSField] = fields or []

    @property
    def data(self) -> dict:
        return {
            FormKeys.ORGANIZATION: self.organization,
            FormKeys.INTERNAL_NAME: single_translation(self.title),
            FormKeys.EXTERNAL_TITLE: self.title,
            FormKeys.FIELDS: [field.data for field in self.fields],
        }

    def is_changed(self, existing: dict) -> bool:
        """Check if current data has values that differs from existing data.

        Does not check keys that are not included in self.data.
        """
        data = self.data
        flat_existing = flatten_dict(existing)
        flat_data = flatten_dict(data)

        if len(existing[FormKeys.FIELDS]) != len(data[FormKeys.FIELDS]):
            return True

        changed = set()
        for key, value in flat_data.items():
            if flat_existing.get(key) != value:
                changed.add(key)

        if changed:
            logger.info(f"Changed values in REMS form: {changed}")

        return bool(changed)
