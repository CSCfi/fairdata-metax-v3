from rest_framework import serializers

from apps.users.models import MetaxUser


class MetaxUserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaxUser
        fields = (
            "id",
            "username",
        )
