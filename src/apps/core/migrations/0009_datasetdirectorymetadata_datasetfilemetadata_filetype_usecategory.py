# Generated by Django 3.2.16 on 2023-02-17 07:56

import django.db.models.deletion
from django.db import migrations, models

import apps.core.models.concepts


class Migration(migrations.Migration):

    dependencies = [
        ('refdata', '0004_auto_20230208_0959'),
        ('files', '0004_auto_20230210_1559'),
        ('core', '0008_auto_20230222_1549'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileType',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=(apps.core.models.concepts.ConceptProxyMixin, 'refdata.filetype'),
        ),
        migrations.CreateModel(
            name='UseCategory',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=(apps.core.models.concepts.ConceptProxyMixin, 'refdata.usecategory'),
        ),
        migrations.CreateModel(
            name='DatasetDirectoryMetadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('directory_path', models.TextField(db_index=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('dataset', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='directory_metadata', to='core.dataset')),
                ('storage_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.storageproject')),
                ('use_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usecategory')),
            ],
        ),
        migrations.CreateModel(
            name='DatasetFileMetadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='file_metadata', to='core.dataset')),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dataset_metadata', to='files.file')),
                ('file_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.filetype')),
                ('use_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usecategory')),
            ],
            options={
                'unique_together': {('dataset', 'file')},
            },
        ),
    ]