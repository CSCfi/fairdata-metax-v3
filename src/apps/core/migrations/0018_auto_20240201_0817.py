# Generated by Django 3.2.22 on 2024-02-01 08:17

import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20240123_1332'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalogrecord',
            name='metadata_owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='core.metadataprovider'),
        ),
        migrations.AlterField(
            model_name='provenance',
            name='description',
            field=django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"description", "fi": "kuvaus"}', null=True),
        ),
    ]