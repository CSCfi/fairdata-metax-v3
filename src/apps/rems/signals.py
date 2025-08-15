from django.conf import settings
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.rems.rems_service import REMSService
from apps.users.models import MetaxUser

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MetaxUser)
def handle_user_updated(*args, instance: MetaxUser, created: bool, **kwargs):
    """When user dac_organizations change, update REMS workflows for related organizations."""
    if not settings.REMS_ENABLED:
        return

    has_changed = instance.tracker.has_changed("dac_organizations")
    if not (created or has_changed):
        return

    # Collect both old (may have been removed) and new (may have been added) organizations
    old_orgs = set(instance.tracker.changed().get("dac_organizations", []))
    orgs = sorted(old_orgs | set(instance.dac_organizations))

    for org in orgs:
        workflows = REMSService().update_organization_workflows(org)
        for workflow in workflows:
            logger.info(f"Updated REMS workflow {workflow.key} (rems_id={workflow.rems_id})")
