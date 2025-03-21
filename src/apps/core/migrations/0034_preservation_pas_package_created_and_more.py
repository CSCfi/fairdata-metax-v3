# Generated by Django 4.2.16 on 2024-12-04 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_remove_contract_identifier'),
    ]

    operations = [
        migrations.AddField(
            model_name='preservation',
            name='pas_package_created',
            field=models.BooleanField(default=False, help_text='After a PAS package has been created, further changes to the dataset metadata will not be visible in the package.'),
        ),
        migrations.AddField(
            model_name='preservation',
            name='pas_process_running',
            field=models.BooleanField(default=False, help_text='Only PAS service is allowed to update the dataset while PAS is processing it.'),
        ),
    ]
