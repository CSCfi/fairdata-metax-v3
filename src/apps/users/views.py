from django.contrib.auth import logout
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from apps.users.authentication import SSOAuthentication
from apps.users.serializers import UserInfoSerializer


class TokenObtainPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class DecoratedTokenObtainPairView(TokenObtainPairView):
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: TokenObtainPairResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class DecoratedTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: TokenRefreshResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenVerifyResponseSerializer(serializers.Serializer):
    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class DecoratedTokenVerifyView(TokenVerifyView):
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: TokenVerifyResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenBlacklistResponseSerializer(serializers.Serializer):
    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class DecoratedTokenBlacklistView(TokenBlacklistView):
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: TokenBlacklistResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LoginView(APIView):
    def get(self, request):
        authentication = SSOAuthentication()
        if not authentication.is_sso_enabled():
            raise exceptions.MethodNotAllowed(method=request.method)

        url = authentication.sso_login_url(request)
        return redirect(url)


class LogoutView(APIView):
    def post(self, request):
        logout(request)  # Clear DRF login session if it exists

        # Redirect to SSO logout if using SSO login
        authenticator = request.successful_authenticator
        if isinstance(request.successful_authenticator, SSOAuthentication):
            url = authenticator.sso_logout_url(request)
            return redirect(url)

        return redirect("/")


class UserView(APIView):
    def get(self, request):
        """Return user session information."""
        if not request.user.is_authenticated:
            raise exceptions.NotAuthenticated()

        serializer = UserInfoSerializer(request.user, context={"request": request})
        return Response(serializer.data)
