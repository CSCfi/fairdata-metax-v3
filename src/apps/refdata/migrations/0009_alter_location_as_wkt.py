# Generated by Django 3.2.19 on 2023-05-11 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refdata', '0008_merge_0005_auto_20230315_1529_0007_auto_20230328_1250'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='as_wkt',
            field=models.TextField(blank=True, null=True),
        ),
    ]