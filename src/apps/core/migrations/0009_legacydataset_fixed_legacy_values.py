# Generated by Django 4.2.11 on 2024-03-27 15:09

import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_datasetlicense_title_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='legacydataset',
            name='fixed_legacy_values',
            field=models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True),
        ),
    ]
