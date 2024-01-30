from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.


class SystemCreatorBaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.system_creator = request.user
        super().save_model(request, obj, form, change)


class AbstractDatasetPropertyBaseAdmin(SystemCreatorBaseAdmin, SimpleHistoryAdmin):
    list_filter = ("created", "modified")
    exclude = ("is_removed", "removed")
