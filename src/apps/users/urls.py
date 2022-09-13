from django.urls import path
from rest_framework.authtoken import views


urlpatterns = [
    path("", views.obtain_auth_token),
]
