# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from django.utils.translation import gettext_lazy as _

from apps.common.serializers.serializers import CommonModelSerializer, StrictSerializer
from apps.core.models.concepts import FileType, UseCategory
from apps.core.models.file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata


class FileMetadataSerializer(CommonModelSerializer):
    file_type = FileType.get_serializer_class()(required=False)
    use_category = UseCategory.get_serializer_class()(required=True)

    class Meta:
        model = FileSetFileMetadata
        fields = ["title", "description", "file_type", "use_category"]


class DirectoryMetadataSerializer(CommonModelSerializer):
    use_category = UseCategory.get_serializer_class()(required=True)

    class Meta:
        model = FileSetDirectoryMetadata
        fields = ["title", "description", "use_category"]
