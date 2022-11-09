"""metax_service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from apps.core.core_urls import urlpatterns as core_urls


schema_view = get_schema_view(
    openapi.Info(
        title="Metax Service",
        default_version="v3",
        description="Metadata storage for Finnish research data",
        license=openapi.License(name="GNU GPLv2 License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


urlpatterns = [
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
    path("reference_data/", include("refdata.urls")),
    path("actors/", include("actors.urls")),
    path("rest/v3/", include(core_urls)),
    path("auth/", include("users.urls")),
]
