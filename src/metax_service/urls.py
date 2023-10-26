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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.authtoken import views
from rest_framework.schemas import get_schema_view as drf_schema_view

from apps.core.views import IndexView
from apps.router.urls import urlpatterns as router_urls

openapi_info = openapi.Info(
    title="Metax Service",
    default_version="v3",
    description="Metadata storage for Finnish research data",
    license=openapi.License(name="GNU GPLv2 License"),
)
schema_view = get_schema_view(
    openapi_info,
    public=True,
    permission_classes=[permissions.AllowAny],
)


urlpatterns = [
    path("", IndexView.as_view()),
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
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("schema/", drf_schema_view()),
    re_path(r"^watchman/", include("watchman.urls")),
    path("admin/", admin.site.urls),
    path("v3/", include(router_urls)),
    path("auth/", include("users.urls")),
    path("hijack/", include("hijack.urls")),
]
if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns = urlpatterns + [path("__debug__/", include("debug_toolbar.urls"))]

if settings.ENABLE_SILK_PROFILER:
    urlpatterns = urlpatterns + [path("silk/", include("silk.urls", namespace="silk"))]

if settings.NO_NGINX_PROXY:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.ENABLE_DRF_TOKEN_AUTH:
    urlpatterns = urlpatterns + [path("drf-token-auth/", views.obtain_auth_token)]
