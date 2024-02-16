# Generated by Django 3.2.22 on 2024-02-08 13:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0018_auto_20240201_0817'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='other_versions',
        ),
        migrations.AddField(
            model_name='dataset',
            name='version',
            field=models.IntegerField(blank=True, default=1, editable=False),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='version',
            field=models.IntegerField(blank=True, default=1, editable=False),
        ),
        migrations.CreateModel(
            name='DatasetVersions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('system_creator', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='core_datasetversionss', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='dataset',
            name='dataset_versions',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='datasets', to='core.datasetversions'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='dataset_versions',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datasetversions'),
        ),
    ]