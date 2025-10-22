from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.


class SystemCreatorBaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.system_creator = request.user
        super().save_model(request, obj, form, change)


class CommonAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        # Add help text to indicate what fields are used in the search
        if self.search_fields and not self.search_help_text:
            self.search_help_text = f"Searched fields: {', '.join(self.search_fields)}"
        super().__init__(model, admin_site)


class AbstractDatasetPropertyBaseAdmin(SystemCreatorBaseAdmin, SimpleHistoryAdmin, CommonAdmin):
    list_filter = ("created", "modified")
    exclude = ("removed",)
