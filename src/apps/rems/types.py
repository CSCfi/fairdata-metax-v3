from dataclasses import dataclass
from typing import List, Optional

from django.db import models


class LicenseType(models.TextChoices):
    link = "link"  # textcontent is an URL pointing to the license
    text = "text"  # textcontent is an license text
    attachment = "attachment"  # license has file attachment (not implemented in Metaxx)


@dataclass
class ApplicationLicenseData:
    """Application license data for end users."""

    id: int
    type: LicenseType
    title: dict  # Lang -> title
    text: Optional[dict] = None  # Lang -> text content
    link: Optional[dict] = None  # Lang -> link
    is_data_access_terms: bool = False  # Field added by Metax
    # - Organization is omitted here since it's the Metax REMS manager organization,
    #   and not relevant for users.
    # - Attachment not supported, would have license/attachment-id and license/attachment-filename

    @classmethod
    def from_rems_license_data(cls, data: dict, is_data_access_terms=False):
        """Convert license from format provided in REMS /api/licenses."""
        title = {}
        textcontent = {}
        for lang, loc in data["localizations"].items():
            title[lang] = loc.get("title")
            textcontent[lang] = loc.get("textcontent")

        licensetype = data["licensetype"]
        optional = {}
        if licensetype == LicenseType.text:
            optional["text"] = textcontent
        elif licensetype == LicenseType.link:
            optional["link"] = textcontent

        return cls(
            id=data["id"],
            type=data["licensetype"],
            title=title,
            is_data_access_terms=is_data_access_terms,
            **optional,
        )


@dataclass
class ApplicationBase:
    """Data needed for submitting an application for end Fusers."""

    licenses: List[ApplicationLicenseData]
    forms: List[dict]
