# Generated by Django 4.2.11 on 2024-03-19 09:32

import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ContributorRole',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ContributorType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventOutcome',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FieldOfScience',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
                ('is_essential_choice', models.BooleanField(default=False, help_text='If the field of science should be selectable in model forms')),
            ],
            options={
                'verbose_name': 'field of science',
                'verbose_name_plural': 'fields of science',
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FileFormatVersion',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
                ('file_format', models.CharField(max_length=255)),
                ('format_version', models.CharField(blank=True, default='', max_length=255)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FileType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FunderType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IdentifierType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
                ('is_essential_choice', models.BooleanField(default=False, help_text='If the language should be selectable in model forms')),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='License',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LifecycleEvent',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
                ('as_wkt', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PreservationEvent',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RelationType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ResearchInfra',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ResourceType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RestrictionGrounds',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
            ],
            options={
                'verbose_name': 'restriction grounds',
                'verbose_name_plural': 'restriction grounds',
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Theme',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
                ('is_essential_choice', models.BooleanField(default=False, help_text='If the theme should be selectable in model forms')),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UseCategory',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=255)),
                ('in_scheme', models.URLField(blank=True, default='', max_length=255)),
                ('pref_label', django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')),
                ('same_as', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('deprecated', models.DateTimeField(blank=True, help_text='If set, entry is not shown in reference data list by default.', null=True)),
                ('broader', models.ManyToManyField(blank=True, related_name='narrower', to='refdata.usecategory')),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]