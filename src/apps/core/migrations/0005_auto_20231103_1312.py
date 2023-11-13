# Generated by Django 3.2.22 on 2023-11-03 13:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_catalogrecord_data_catalog'),
    ]

    operations = [
        migrations.AddField(
            model_name='accessrights',
            name='available',
            field=models.DateField(blank=True, help_text='Date (UTC) that the resource became or will become available.', null=True),
        ),
        migrations.AddField(
            model_name='historicalaccessrights',
            name='available',
            field=models.DateField(blank=True, help_text='Date (UTC) that the resource became or will become available.', null=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='access_rights',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='datasets', to='core.accessrights'),
        ),
    ]