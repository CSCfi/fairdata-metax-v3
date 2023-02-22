from django.shortcuts import render
from rest_framework.pagination import PageNumberPagination

# Create your views here.


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000
