# Generated by Django 4.2.11 on 2024-04-03 08:11

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_rename_ignored_legacy_values_legacydataset_invalid_legacy_values'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='bibliographic_citation',
            field=models.TextField(blank=True, null=True, validators=[django.core.validators.MinLengthValidator(1)]),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='bibliographic_citation',
            field=models.TextField(blank=True, null=True, validators=[django.core.validators.MinLengthValidator(1)]),
        ),
    ]
