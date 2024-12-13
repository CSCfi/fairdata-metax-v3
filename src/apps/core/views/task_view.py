import logging

from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_q.models import Task
from rest_framework import serializers

from apps.common.views import CommonReadOnlyModelViewSet
from apps.core.permissions import TaskAccessPolicy

logger = logging.getLogger(__name__)


class TaskFilterSet(filters.FilterSet):
    success = filters.BooleanFilter()  # Query with success=False to find failed tasks
    ordering = filters.OrderingFilter(fields=("stopped", "started"))


class TaskSerializer(serializers.ModelSerializer):
    args = serializers.CharField(read_only=True)
    kwargs = serializers.CharField(read_only=True)
    result = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "func",
            "args",
            "kwargs",
            "result",
            "name",
            "hook",
            "group",
            "cluster",
            "started",
            "stopped",
            "success",
            "attempt_count",
        ]


class TaskViewSet(CommonReadOnlyModelViewSet):
    """Basic read-only tasks view."""

    queryset = Task.objects.all()
    filterset_class = TaskFilterSet
    serializer_class = TaskSerializer
    access_policy = TaskAccessPolicy
    http_method_names = ["get"]
