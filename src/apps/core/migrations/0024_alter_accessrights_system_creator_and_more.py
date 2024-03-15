# Generated by Django 4.2.11 on 2024-03-18 13:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0023_alter_remoteresource_dataset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accessrights',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cataloghomepage',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='catalogrecord',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='contract',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='datacatalog',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='datasetlicense',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='datasetproject',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='datasetpublisher',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='datasetversions',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='entity',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='entityrelation',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='fileset',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='funder',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='funding',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='metadataprovider',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='otheridentifier',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='preservation',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='provenance',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='provenancevariable',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='remoteresource',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='spatial',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='temporal',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
    ]