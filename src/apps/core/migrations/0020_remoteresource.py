# Generated by Django 3.2.21 on 2023-09-22 08:00

import apps.common.models
from django.conf import settings
import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0019_auto_20230919_1229'),
    ]

    operations = [
        migrations.CreateModel(
            name='RemoteResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('removal_date', models.DateTimeField(blank=True, null=True)),
                ('title', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('description', django.contrib.postgres.fields.hstore.HStoreField(blank=True, help_text='example: {"en":"description", "fi":"kuvaus"}', null=True)),
                ('access_url', models.URLField(blank=True, max_length=2048, null=True)),
                ('download_url', models.URLField(blank=True, max_length=2048, null=True)),
                ('checksum', models.TextField(blank=True, null=True)),
                ('mediatype', models.TextField(blank=True, help_text='IANA media type as a string, e.g. "text/csv".', null=True, validators=[apps.common.models.MediaTypeValidator()])),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remote_resources', to='core.dataset')),
                ('file_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.filetype')),
                ('system_creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='core_remoteresources', to=settings.AUTH_USER_MODEL)),
                ('use_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.usecategory')),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
