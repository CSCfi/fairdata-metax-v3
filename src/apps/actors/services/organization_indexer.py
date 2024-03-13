import csv
import logging

import requests
from cachalot.api import cachalot_disabled
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.actors.models import Organization
from metax_service.settings.components.actors import ORGANIZATION_SCHEME

_logger = logging.getLogger(__name__)


CSV_HEADERS = [
    "org_name_fi",
    "org_name_en",
    "org_name_sv",
    "org_code",
    "unit_main_code",
    "unit_sub_code",
    "unit_name",
    "org_isni",
    "org_csc",
]


class OrganizationIndexer:
    """Load organizations and up to one level of suborganizations."""

    def fetch_orgs_from_api(self):
        """Fetch organizations from API and write to csv file."""
        _logger.info(f"Fetching organization data from {settings.ORGANIZATION_FETCH_API_URL}")
        res = requests.get(settings.ORGANIZATION_FETCH_API_URL)
        data = res.json()

        orgs_json = data["hits"]["hits"]
        orgs = []

        for org in orgs_json:
            org_source = org["_source"]

            name_fi = str(org_source["nameFi"]).strip()
            name_en = str(org_source["nameEn"]).strip()
            name_sv = str(org_source.get("nameSv")).strip()
            org_code = str(org_source["organizationId"]).strip()

            organization = {
                "org_name_fi": name_fi,
                "org_name_en": name_en,
                "org_name_sv": name_sv,
                "org_code": org_code,
            }
            orgs.append(organization)

            sub_units = org_source.get("subUnits") or []
            for sub_unit in sub_units:
                unit_sub_code = str(sub_unit["subUnitID"]).strip()
                unit_name = str(sub_unit["subUnitName"]).strip()

                sub_organization = {
                    **organization,
                    "unit_name": unit_name,
                    "unit_sub_code": unit_sub_code,
                }
                orgs.append(sub_organization)

        orgs = sorted(orgs, key=lambda org: (org["org_name_fi"], org.get("unit_name", "")))

        _logger.info(f"Retrieved {len(orgs)} organizations.")
        if settings.ORGANIZATION_DATA_FILE:
            with open(settings.ORGANIZATION_DATA_FILE, "w") as f:
                writer = csv.DictWriter(
                    f, delimiter=",", quotechar='"', lineterminator="\n", fieldnames=CSV_HEADERS
                )
                writer.writeheader()
                writer.writerows(orgs)
            _logger.info(f"CSV updated.")
        return orgs

    def row_to_dict(self, org: dict):
        """Convert organizations.csv style org to format closer to Metax."""
        org_name_fi = org.get("org_name_fi", "")
        org_name_en = org.get("org_name_en", "")
        org_name_sv = org.get("org_name_sv", "")
        main_org_code = org.get("org_code", "")
        # unit_main_code is unused
        unit_sub_code = org.get("unit_sub_code", "")
        unit_name = org.get("unit_name", "").rstrip()
        org_isni = org.get("org_isni", "")
        org_csc = org.get("org_csc", "")

        label = {
            "fi": org_name_fi,
            "und": org_name_fi,
        }

        if org_name_en:
            label["en"] = org_name_en

        if org_name_sv:
            label["sv"] = org_name_sv

        org_code = main_org_code
        parent_org_code = None
        if unit_sub_code:
            org_code = f"{org_code}-{unit_sub_code}"
            parent_org_code = main_org_code
            label = {
                "en": unit_name,
                "fi": unit_name,
                "sv": unit_name,
                "und": unit_name,
            }

        url = f"{settings.ORGANIZATION_BASE_URI}{org_code}"
        parent_url = (
            f"{settings.ORGANIZATION_BASE_URI}{parent_org_code}" if parent_org_code else None
        )
        org = {
            "url": url,
            "pref_label": label,
            "code": org_code,
            "parent": parent_url,
            "isni": org_isni,  # not used currently
            "csc": org_csc,  # not used currently
            "in_scheme": settings.ORGANIZATION_SCHEME,
        }
        return org

    def get_orgs_from_csv(self):
        _logger.info(f"Reading organizations from csv")
        with open(settings.ORGANIZATION_DATA_FILE) as f:
            reader = csv.DictReader(f, delimiter=",", quotechar='"', lineterminator="\n")
            return list(reader)

    def orgs_list_to_dict(self, orgs: list):
        orgs_dict = {}
        for org in orgs:
            org = self.row_to_dict(org)
            if existing := orgs_dict.get(org["url"]):
                label = org.get("pref_label", {}).get("en")
                existing_label = existing.get("pref_label", {}).get("en")
                _logger.warning(
                    f"Duplicate organization URL, skipping: {org['url']} {label}, existing: {existing_label}"
                )
            else:
                orgs_dict[org["url"]] = org
        _logger.info(f"Loaded {len(orgs_dict)} organizations.")
        return orgs_dict

    def sort_parents_first(self, orgs_dict):
        """Sort organizations so main organizations listed first."""
        return sorted(orgs_dict.values(), key=lambda x: x["parent"] is not None)

    @transaction.atomic
    def update_orgs(self, orgs_dict):
        all_reference_orgs = Organization.all_objects.filter(
            is_reference_data=True, in_scheme=settings.ORGANIZATION_SCHEME
        )

        # Deprecate organizations that have been removed from source data
        new_deprecated = all_reference_orgs.filter(deprecated__isnull=True).exclude(
            url__in=orgs_dict.keys()
        )
        if count := new_deprecated.count():
            _logger.info(
                f"Reference data organizations in database but no longer in source data: {count}"
            )
            new_deprecated.update(deprecated=timezone.now())

        existing_orgs = all_reference_orgs.filter(url__in=orgs_dict.keys())
        orgs_by_url = {org.url: org for org in existing_orgs}

        # create parent organizations first so children can refer to them
        orgs_parents_first = self.sort_parents_first(orgs_dict)

        for org_dict in orgs_parents_first:
            url = org_dict["url"]
            org = orgs_by_url.get(url)
            is_new = not org
            if is_new:
                org = Organization(url=url, is_reference_data=True)
                orgs_by_url[url] = org

            org.in_scheme = org_dict.get("in_scheme")
            org.code = org_dict.get("code")
            org.same_as = []
            org.pref_label = org_dict["pref_label"]
            org.deprecated = None
            if parent := org_dict.get("parent"):
                org.parent = orgs_by_url[parent]
            else:
                org.parent = None

            org.save()
        _logger.info(f"Organizations updated")

    def index(self, cached=False):
        orgs: list
        if cached:
            orgs = self.get_orgs_from_csv()
        else:
            orgs = self.fetch_orgs_from_api()

        orgs_dict = self.orgs_list_to_dict(orgs)
        with cachalot_disabled():
            self.update_orgs(orgs_dict)
