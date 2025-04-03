from django.conf import settings
from django.core.management import BaseCommand

from apps.rems.models import REMSEntity
from apps.rems.rems_service import REMSService


class Command(BaseCommand):
    def create_approver_bot(self) -> REMSEntity:
        """Create user that approves applications automatically."""
        # See https://github.com/CSCfi/rems/blob/master/docs/bots.md
        return self.service.create_user(userid="approver-bot", name="Approver Bot", email=None)

    def handle(self, *args, **options):
        self.service = REMSService()
        self.service.create_organization(
            organization_id=settings.REMS_ORGANIZATION_ID,
            short_name={"en": "CSC", "fi": "CSC"},
            name={
                "en": "CSC – IT Center for Science",
                "fi": "CSC – Tieteen tietotekniikan keskus",
            },
        )
        self.create_approver_bot()
        self.service.create_workflow(
            key="automatic",
            title="Fairdata Automatic",
            handlers=["approver-bot"],
        )
