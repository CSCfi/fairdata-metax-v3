# Generated by Django 4.2.11 on 2024-05-20 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0003_remove_file_is_removed'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='published',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
