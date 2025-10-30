from apps.common.filters import MultipleCharFilter
from apps.common.views import CommonModelViewSet
from apps.core.serializers import OrganizationStatisticsSerializer, ProjectStatisticsSerializer
from apps.core.models import OrganizationStatistics, ProjectStatistics

from django_filters import rest_framework as filters
from rest_framework import viewsets


class OrganizationStatisticsFilter(filters.FilterSet):
    organizations = MultipleCharFilter(field_name="organization")


class ProjectStatisticsFilter(filters.FilterSet):
    projects = MultipleCharFilter(field_name="project_identifier")


class OrganizationStatisticsViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationStatisticsSerializer
    queryset = OrganizationStatistics.objects.all()
    filterset_class = OrganizationStatisticsFilter
    http_method_names = ["get"]


class ProjectStatisticsViewSet(CommonModelViewSet):
    serializer_class = ProjectStatisticsSerializer
    queryset = ProjectStatistics.objects.all()
    filterset_class = ProjectStatisticsFilter
    http_method_names = ["get"]
