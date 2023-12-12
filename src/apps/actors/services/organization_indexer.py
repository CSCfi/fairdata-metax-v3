import csv
import logging

from cachalot.api import cachalot_disabled
from django.conf import settings
from django.db import transaction

from apps.actors.models import Organization
from metax_service.settings.components.actors import ORGANIZATION_SCHEME

_logger = logging.getLogger(__name__)


class OrganizationIndexer:
    """Load organizations and up to one level of suborganizations from csv file"""

    def row_to_dict(self, row):
        org_name_fi = row.get("org_name_fi", "")
        org_name_en = row.get("org_name_en", "")
        org_name_sv = row.get("org_name_sv", "")
        main_org_code = row.get("org_code", "")
        # unit_main_code is unused
        unit_sub_code = row.get("unit_sub_code", "")
        unit_name = row.get("unit_name", "").rstrip()
        org_isni = row.get("org_isni", "")
        org_csc = row.get("org_csc", "")

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

    def read_organizations(self):
        orgs_dict = {}
        with open(settings.ORGANIZATION_DATA_FILE) as f:
            reader = csv.DictReader(f, delimiter=",", quotechar='"')
            for row in reader:
                org = self.row_to_dict(row)
                if orgs_dict.get(org["url"]):
                    label = org.get("pref_label", {}).get("en")
                    _logger.warning(f"Duplicate ogranization URL, skipping: {org['url']} {label}")
                else:
                    orgs_dict[org["url"]] = org
        return orgs_dict

    def sort_parents_first(self, orgs_dict):
        """Sort organizations so main organizations listed first."""
        return sorted(orgs_dict.values(), key=lambda x: x["parent"] is not None)

    @transaction.atomic
    def update_orgs(self, orgs_dict):
        all_reference_orgs = Organization.all_objects.filter(
            is_reference_data=True, in_scheme=settings.ORGANIZATION_SCHEME
        )
        deprecated = all_reference_orgs.exclude(url__in=orgs_dict.keys())
        for org in deprecated:
            if not org.is_removed:
                org.is_removed = True
                org.save()

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
            if parent := org_dict.get("parent"):
                org.parent = orgs_by_url[parent]
            else:
                org.parent = None
            org.save()

    def index(self):
        orgs_dict = self.read_organizations()
        with cachalot_disabled():
            self.update_orgs(orgs_dict)
