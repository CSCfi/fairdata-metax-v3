from django.urls import path
from rest_framework.authtoken import views
from apps.users.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("simple/", views.obtain_auth_token),
    path("jwt/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
