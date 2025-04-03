import logging

from django.contrib import admin

from apps.common.admin import AbstractDatasetPropertyBaseAdmin

# Register your models here.
from apps.rems.models import (
    REMSCatalogueItem,
    REMSForm,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)

logger = logging.getLogger(__name__)


class REMSEntityAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(REMSUser)
class REMSUserAdmin(REMSEntityAdmin):
    pass


@admin.register(REMSOrganization)
class REMSOrganizationAdmin(REMSEntityAdmin):
    pass


@admin.register(REMSWorkflow)
class REMSWorkflowAdmin(REMSEntityAdmin):
    pass


@admin.register(REMSForm)
class REMSFormAdmin(REMSEntityAdmin):
    pass


@admin.register(REMSLicense)
class REMSLicenseAdmin(REMSEntityAdmin):
    pass


@admin.register(REMSResource)
class REMSResourceAdmin(REMSEntityAdmin):
    pass


@admin.register(REMSCatalogueItem)
class REMSCatalogueItemAdmin(REMSEntityAdmin):
    pass
