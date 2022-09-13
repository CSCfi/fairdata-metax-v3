import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from model_utils.models import SoftDeletableModel


class MetaxUser(AbstractUser, SoftDeletableModel):
    """Basic Metax User."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # if True, don't display User details
    is_hidden = models.BooleanField(default=False)

    def undelete(self):
        self.is_removed = False
        self.is_hidden = False
        self.save()

    def __str__(self):
        return self.username
