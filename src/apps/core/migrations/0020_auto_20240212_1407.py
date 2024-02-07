# Generated by Django 3.2.22 on 2024-02-12 14:07

import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_auto_20240208_1357'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accessrights',
            name='access_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='access_rights', to='core.accesstype'),
        ),
        migrations.AlterField(
            model_name='datacatalog',
            name='access_rights',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='catalogs', to='core.accessrights'),
        ),
        migrations.AlterField(
            model_name='datacatalog',
            name='publisher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='catalogs', to='core.datasetpublisher'),
        ),
        migrations.AlterField(
            model_name='provenance',
            name='description',
            field=django.contrib.postgres.fields.hstore.HStoreField(blank=True, help_text='example: {"en":"description", "fi": "kuvaus"}', null=True),
        ),
        migrations.AlterField(
            model_name='provenance',
            name='is_associated_with',
            field=models.ManyToManyField(blank=True, related_name='provenance', to='core.DatasetActor'),
        ),
        migrations.AlterField(
            model_name='provenance',
            name='title',
            field=django.contrib.postgres.fields.hstore.HStoreField(blank=True, help_text='example: {"en":"title", "fi":"otsikko"}', null=True),
        ),
    ]
