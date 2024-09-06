# Generated by Django 4.2.11 on 2024-05-30 09:25

from django.conf import settings
import django.contrib.postgres.fields
import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid

def copy_to_new(apps, schema_editor):
    old = apps.get_model("core", "LegacyDataset")
    new = apps.get_model("core", "LegacyDatasetNew")
    new_objs = []
    fields = [f.attname for f in old._meta.local_concrete_fields]
    for old_obj in old.objects.all():
        new_obj = new(**{k:v for k,v in old_obj.__dict__.items() if k in fields})
        new_obj.id = old_obj.dataset_id
        new_objs.append(new_obj)
    new.objects.bulk_create(new_objs)

    # check dataset relations have been migrated correctly
    old_dataset_ids = old.objects.order_by("dataset__id").values_list("dataset__id", flat=True)
    new_dataset_ids = new.objects.order_by("dataset__id").values_list("dataset__id", flat=True)
    assert list(old_dataset_ids) == list(new_dataset_ids)

    # check ids match dataset ids
    new_dataset_ids = new.objects.order_by("dataset__id").values_list("dataset__id", flat=True)
    new_ids = new.objects.order_by("id").values_list("id", flat=True)
    assert list(new_dataset_ids) == list(new_ids)

def copy_to_old(apps, schema_editor):
    old = apps.get_model("core", "LegacyDataset")
    new = apps.get_model("core", "LegacyDatasetNew")
    fields = [f.attname for f in old._meta.local_concrete_fields]
    for new_obj in new.objects.all():
        values = {k:v for k,v in new_obj.__dict__.items() if k in fields}
        old_obj = old(**values) # assign values from LegacyDatasetNew
        old_obj.__dict__.update(new_obj.dataset.__dict__) # assign values from dataset
        old_obj.save() # no bulk create for multi-table models, need to do it the slow way :(

    # check dataset relations have been migrated correctly
    old_dataset_ids = old.objects.order_by("dataset__id").values_list("dataset__id", flat=True)
    new_dataset_ids = new.objects.order_by("dataset__id").values_list("dataset__id", flat=True)
    assert list(old_dataset_ids) == list(new_dataset_ids)



class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0016_remove_legacydataset_files_json_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LegacyDatasetNew',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('dataset_json', models.JSONField(encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('contract_json', models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('legacy_file_ids', django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(), blank=True, null=True, size=None)),
                ('v2_dataset_compatibility_diff', models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Difference between v1-v2 and V3 dataset json', null=True)),
                ('migration_errors', models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('last_successful_migration', models.DateTimeField(blank=True, null=True)),
                ('invalid_legacy_values', models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('fixed_legacy_values', models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('dataset', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.dataset')),
                ('system_creator', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created', 'id'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.RunPython(copy_to_new, copy_to_old),
        migrations.DeleteModel('LegacyDataset'),
        migrations.RenameModel('LegacyDatasetNew', 'LegacyDataset'),
    ]