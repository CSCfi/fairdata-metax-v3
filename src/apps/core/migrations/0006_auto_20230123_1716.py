# Generated by Django 3.2.16 on 2023-01-23 15:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20230123_1645'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='publisher',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='publisher',
        ),
    ]