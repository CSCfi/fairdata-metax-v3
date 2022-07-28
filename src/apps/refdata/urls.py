"""refdata URL Configuration

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
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.refdata.views import get_viewset_for_model
from apps.refdata.models import FieldOfScience, Language, Keyword, Location


router = DefaultRouter(trailing_slash=False)
router.register("field_of_science/?", get_viewset_for_model(FieldOfScience))
router.register("language/?", get_viewset_for_model(Language))
router.register("keyword/?", get_viewset_for_model(Keyword))
router.register("location/?", get_viewset_for_model(Location))


urlpatterns = [path("", include(router.urls))]
