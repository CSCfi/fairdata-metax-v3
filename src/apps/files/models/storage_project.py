# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import re
import uuid
from typing import Set

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

    def get_directory_paths(self, dataset=None) -> Set[str]:
        """Get directory paths used in the project as a set.

        If dataset is supplied, return only directories belonging to dataset.
        Otherwise all directories are returned."""
        qs = self.files
        if dataset:
            qs = qs.filter(datasets=dataset)
        file_directory_paths = (
            qs.values_list("directory_path", flat=True)
            .order_by("directory_path")
            .distinct("directory_path")
        )
        all_paths = set(file_directory_paths)

        # Add intermediate directories that don't have files directly but in subdirs.
        last_part = re.compile("/[^/]+/$")  # matches e.g. `/subdir/` for `/dir/subdir/`
        for path in file_directory_paths:
            # Remove last path part and add to set until encountering path already in set.
            path = last_part.sub("/", path, count=1)
            while path not in all_paths:
                all_paths.add(path)
                path = last_part.sub("/", path, count=1)
        return all_paths
