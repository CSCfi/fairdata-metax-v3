# Generated by Django 4.2.16 on 2024-10-07 12:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_datacatalog_publishing_channels_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dataset',
            old_name='pid_type',
            new_name='generate_pid_on_publish',
        ),
        migrations.RenameField(
            model_name='historicaldataset',
            old_name='pid_type',
            new_name='generate_pid_on_publish',
        ),
    ]
