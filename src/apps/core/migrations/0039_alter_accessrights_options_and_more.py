# Generated by Django 4.2.16 on 2024-12-18 12:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_alter_dataset_field_of_science_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='accessrights',
            options={'ordering': ['created', 'id'], 'verbose_name_plural': 'Access rights'},
        ),
        migrations.AlterModelOptions(
            name='historicalaccessrights',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical access rights', 'verbose_name_plural': 'historical Access rights'},
        ),
    ]
