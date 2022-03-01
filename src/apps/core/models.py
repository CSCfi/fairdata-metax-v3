from django.contrib.postgres.fields import HStoreField, ArrayField
from django.db import models

# Create your models here.
from django.db import models

# Create your models here.
from model_utils.models import TimeStampedModel, SoftDeletableModel


class AbstractBaseModel(TimeStampedModel, SoftDeletableModel):
    class Meta:
        abstract = True
        get_latest_by = "created"
        ordering = ["created"]


class DatasetPublisher(AbstractBaseModel):
    name = HStoreField()


class DataCatalog(AbstractBaseModel):
    identifier = models.CharField(max_length=255, primary_key=True)
    dataset_versioning = models.BooleanField(default=False)
    harvested = models.BooleanField(default=False)
    title = HStoreField()
    language = ArrayField(base_field=HStoreField)

    class DatasetSchemaChoices(models.TextChoices):
        SCHEMA_IDA = "ida"
        SCHEMA_ATT = "att"
        SCHEMA_DRF = "drf"

    DATASET_SCHEMA_CHOICES = ((DatasetSchemaChoices.SCHEMA_IDA, "IDA Schema"), (DatasetSchemaChoices.SCHEMA_ATT, "ATT Schema"), (DatasetSchemaChoices.SCHEMA_DRF, "DRF Schema"))

    research_dataset_schema = models.CharField(choices=DATASET_SCHEMA_CHOICES, default=DatasetSchemaChoices.SCHEMA_IDA, max_length=6)
