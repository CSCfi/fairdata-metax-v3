from uuid import uuid4

from django.db import models

from apps.common.copier import ModelCopier
from apps.core.models.concepts import SensitivityRationale


class DatasetSensitivityRationale(models.Model):
    copier = ModelCopier(copied_relations=[], parent_relations=["dataset"])

    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, serialize=False)

    rationale = models.ForeignKey(SensitivityRationale, on_delete=models.CASCADE)
    expiration_date = models.DateField(blank=True, null=True)
    dataset = models.ForeignKey(
        "Dataset", related_name="rationales", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["-expiration_date"]

