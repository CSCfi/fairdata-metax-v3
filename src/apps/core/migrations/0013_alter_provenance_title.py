# Generated by Django 3.2.19 on 2023-08-08 09:31

import django.contrib.postgres.fields.hstore
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20230630_1643'),
    ]

    operations = [
        migrations.AlterField(
            model_name='provenance',
            name='title',
            field=django.contrib.postgres.fields.hstore.HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}', null=True),
        ),
    ]
