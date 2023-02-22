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
import inflection
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.refdata.models import reference_data_models
from apps.refdata.views import get_viewset_for_model

router = DefaultRouter(trailing_slash=False)

for model in reference_data_models:
    underscored = inflection.underscore(model.__name__)  # e.g. field_of_science
    router.register(
        underscored,
        get_viewset_for_model(model),
    )

urlpatterns = [path("", include(router.urls))]
