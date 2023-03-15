# Generated by Django 3.2.16 on 2023-01-17 13:22

import uuid

import django.contrib.postgres.fields.hstore
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('refdata', '0002_auto_20221219_0909'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('removal_date', models.DateTimeField(blank=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(blank=True, max_length=255, null=True)),
                ('code', models.CharField(max_length=64, null=True)),
                ('in_scheme', models.URLField(max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('homepage', django.contrib.postgres.fields.hstore.HStoreField(blank=True, help_text='example: {"title": {"en": "webpage"}, "identifier": "url"}', null=True)),
                ('is_reference_data', models.BooleanField(default=False)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='actors.organization')),
                ('system_creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actors_organizations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
            },
        ),
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('removal_date', models.DateTimeField(blank=True, null=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actor_organizations', to='actors.organization')),
                ('system_creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actors_actors', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actor_users', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['is_reference_data'], name='actors_orga_is_refe_976e52_idx'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['url'], name='actors_orga_url_2ac698_idx'),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('url', ''), _negated=True), ('is_reference_data', False), _connector='OR'), name='actors_organization_require_url'),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.UniqueConstraint(condition=models.Q(('is_reference_data', True)), fields=('url',), name='actors_organization_unique_organization_url'),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('code', ''), _negated=True), ('is_reference_data', False), _connector='OR'), name='actors_organization_require_code'),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.UniqueConstraint(condition=models.Q(('is_reference_data', True)), fields=('code',), name='actors_organization_unique_organization_code'),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('in_scheme', ''), _negated=True), ('is_reference_data', False), _connector='OR'), name='actors_organization_require_reference_data_scheme'),
        ),
    ]
