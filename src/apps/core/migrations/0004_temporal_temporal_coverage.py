# Generated by Django 4.2.11 on 2024-03-22 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='temporal',
            name='temporal_coverage',
            field=models.TextField(blank=True, help_text='Period of time expressed as a string.', null=True),
        ),
    ]
