import logging

from django.dispatch import Signal

logger = logging.getLogger(__name__)

# Sent when files are deleted using the API, list of deleted files provided in `queryset` argument
pre_files_deleted = Signal()
