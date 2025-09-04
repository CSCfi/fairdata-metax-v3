import pytest
from django.core.management import call_command

from apps.rems.models import (
    REMSCatalogueItem,
    REMSForm,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)

pytestmark = [
    pytest.mark.django_db,
]


def test_flush_rems_entities():
    """Flushing should delete all REMS entities from Metax."""
    REMSOrganization.objects.create(rems_id="org")
    REMSUser.objects.create(rems_id="user")
    REMSCatalogueItem.objects.create(rems_id=1)
    REMSForm.objects.create(rems_id=1)
    REMSLicense.objects.create(rems_id=1)
    REMSResource.objects.create(rems_id=1)
    REMSWorkflow.objects.create(rems_id=1)

    call_command("flush_rems_entities")

    assert not REMSOrganization.all_objects.exists()
    assert not REMSUser.all_objects.exists()
    assert not REMSCatalogueItem.all_objects.exists()
    assert not REMSForm.all_objects.exists()
    assert not REMSLicense.all_objects.exists()
    assert not REMSResource.all_objects.exists()
    assert not REMSWorkflow.all_objects.exists()
