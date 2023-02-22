from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin


# Register your models here.


class AbstractDatasetPropertyBaseAdmin(SimpleHistoryAdmin):
    list_filter = ("created", "modified")
    exclude = ("is_removed", "removal_date")
