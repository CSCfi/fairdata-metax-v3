from rest_framework.pagination import LimitOffsetPagination


class OffsetPagination(LimitOffsetPagination):
    default_limit = 100
