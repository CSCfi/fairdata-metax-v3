# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.models import Dataset

logger = logging.getLogger(__name__)


class DatasetAllowedActionsSerializer(serializers.Serializer):
    """List what the current logged in user is allowed to do with the dataset.

    Helps other services determine what actions should be available for
    the user without having to reimplement Metax authorization logic.
    Checks AccessPolicy rules without making an actual request
    by faking the required view and request objects.

    Expects object to be a dataset, so set source="*" when used as a
    dataset serializer field.
    """

    update = serializers.SerializerMethodField()
    download = serializers.SerializerMethodField()

    @property
    def access_policy(self):
        """Get access_policy from viewset while avoiding circular import errors."""
        from apps.core.views import DatasetViewSet

        return DatasetViewSet.access_policy

    def get_update(self, obj: Dataset):
        return self.access_policy().query_object_permission(
            user=self.context["request"].user, object=obj, action="update"
        )

    def get_download(self, obj: Dataset):
        return self.access_policy().query_object_permission(
            user=self.context["request"].user, object=obj, action="<op:download>"
        )


class DatasetAllowedActionsQueryParamsSerializer(serializers.Serializer):
    include_allowed_actions = serializers.BooleanField(
        help_text=_("Include allowed actions for current user. Fairdata internal use."),
        required=False,
    )
