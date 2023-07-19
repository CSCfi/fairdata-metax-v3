from django.urls import path

from apps.users.views import APITokenListView, LoginView, LogoutView, UserView

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("user", UserView.as_view(), name="user"),
    path("tokens", APITokenListView.as_view(), name="tokens"),
]
