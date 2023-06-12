from django.urls import path
from rest_framework.authtoken import views

from apps.users.views import LoginView, LogoutView, TokenObtainPairView, TokenRefreshView, UserView

urlpatterns = [
    path("simple/", views.obtain_auth_token),
    path("jwt/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("user", UserView.as_view(), name="user"),
]
