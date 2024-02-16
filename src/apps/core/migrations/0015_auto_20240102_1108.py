# Generated by Django 3.2.22 on 2024-01-02 11:08

import apps.core.models.concepts
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('refdata', '0002_auto_20231026_1513'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('actors', '0003_auto_20231124_0901'),
        ('core', '0014_auto_20231220_0825'),
    ]

    operations = [
        migrations.CreateModel(
            name='Funder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('funder_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refdata.fundertype')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agencies', to='actors.organization')),
                ('system_creator', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='core_funders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Funding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('removed', models.DateTimeField(blank=True, editable=False, null=True)),
                ('funding_identifier', models.CharField(blank=True, max_length=255, null=True)),
                ('funder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funding', to='core.funder')),
                ('system_creator', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='core_fundings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='projectcontributor',
            name='actor',
        ),
        migrations.RemoveField(
            model_name='projectcontributor',
            name='contribution_type',
        ),
        migrations.RemoveField(
            model_name='projectcontributor',
            name='participating_organization',
        ),
        migrations.RemoveField(
            model_name='projectcontributor',
            name='project',
        ),
        migrations.RemoveField(
            model_name='projectcontributor',
            name='system_creator',
        ),
        migrations.DeleteModel(
            name='ContributorType',
        ),
        migrations.CreateModel(
            name='FunderType',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=(apps.core.models.concepts.ConceptProxyMixin, 'refdata.fundertype'),
        ),
        migrations.RenameField(
            model_name='datasetproject',
            old_name='name',
            new_name='title',
        ),
        migrations.RemoveField(
            model_name='datasetproject',
            name='funder_identifier',
        ),
        migrations.RemoveField(
            model_name='datasetproject',
            name='funder_type',
        ),
        migrations.RemoveField(
            model_name='datasetproject',
            name='funding_agency',
        ),
        migrations.RemoveField(
            model_name='datasetproject',
            name='participating_organization',
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='participating_organizations',
            field=models.ManyToManyField(related_name='projects', to='actors.Organization'),
        ),
        migrations.RemoveField(
            model_name='datasetproject',
            name='dataset',
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='core.dataset'),
        ),
        migrations.DeleteModel(
            name='ProjectContributor',
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='funding',
            field=models.ManyToManyField(related_name='projects', to='core.Funding'),
        ),
    ]