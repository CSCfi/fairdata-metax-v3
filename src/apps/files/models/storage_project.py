# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import uuid

from django.db import models

from apps.common.models import AbstractBaseModel
from .file_storage import FileStorage


class StorageProject(AbstractBaseModel):
    """StorageProject associates files with a project in a file storage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_identifier = models.CharField(max_length=200)
    file_storage = models.ForeignKey(FileStorage, on_delete=models.PROTECT)

    class Meta:
        unique_together = [("project_identifier", "file_storage")]
