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

from apps.refdata.views import ReferenceDataViewSet
from apps.refdata.models import FieldOfScience

urlpatterns = [
    path(
        "field_of_science/",
        ReferenceDataViewSet.as_view(
            actions={"get": "list"},
            queryset=FieldOfScience.available_objects.all(),
            serializer_class=FieldOfScience.get_serializer(),
        ),
        name="field-of-science-list",
    )
]
