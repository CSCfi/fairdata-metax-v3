import logging
import json

from django.contrib import admin
from django.utils.html import format_html


from apps.common.admin import AbstractDatasetPropertyBaseAdmin

# Register your models here.
from apps.rems.models import (
    REMSCatalogueItem,
    REMSEntity,
    REMSForm,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)
from apps.rems.rems_service import REMSService

logger = logging.getLogger(__name__)


class REMSEntityAdmin(AbstractDatasetPropertyBaseAdmin):
    readonly_fields = ("rems_data",)

    def rems_data(self, obj: REMSEntity):
        """Show value entity in REMS."""
        service = REMSService()
        try:
            data = json.dumps(service.get_entity_data(obj), indent=2, ensure_ascii=False)
        except Exception as e:
            data = repr(e)
        return format_html("<pre>{data}</pre>", data=data)


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
