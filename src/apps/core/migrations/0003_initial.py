# Generated by Django 4.2.11 on 2024-03-19 09:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('files', '0002_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('refdata', '0002_initial'),
        ('actors', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='variableuniverse',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='variableconcept',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='temporal',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='temporal', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='temporal',
            name='provenance',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='temporal', to='core.provenance'),
        ),
        migrations.AddField(
            model_name='temporal',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='spatial',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='spatial', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='spatial',
            name='reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='refdata.location'),
        ),
        migrations.AddField(
            model_name='spatial',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='remoteresource',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='remote_resources', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='remoteresource',
            name='file_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.filetype'),
        ),
        migrations.AddField(
            model_name='remoteresource',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='remoteresource',
            name='use_category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.usecategory'),
        ),
        migrations.AddField(
            model_name='provenancevariable',
            name='concept',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.variableconcept'),
        ),
        migrations.AddField(
            model_name='provenancevariable',
            name='provenance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='core.provenance'),
        ),
        migrations.AddField(
            model_name='provenancevariable',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='provenancevariable',
            name='universe',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.variableuniverse'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='provenance', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='event_outcome',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.eventoutcome'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='is_associated_with',
            field=models.ManyToManyField(blank=True, related_name='provenance', to='core.datasetactor'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='lifecycle_event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.lifecycleevent'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='preservation_event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.preservationevent'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='spatial',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='provenance', to='core.spatial'),
        ),
        migrations.AddField(
            model_name='provenance',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='preservation',
            name='contract',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='preservation_entries', to='core.contract'),
        ),
        migrations.AddField(
            model_name='preservation',
            name='dataset_version',
            field=models.OneToOneField(help_text='Link between the dataset stored in DPRES and the originating dataset', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='dataset_origin_version', to='core.preservation'),
        ),
        migrations.AddField(
            model_name='preservation',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='otheridentifier',
            name='identifier_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dataset_identifiers', to='core.identifiertype'),
        ),
        migrations.AddField(
            model_name='otheridentifier',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='metadataprovider',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='metadataprovider',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldatasetpublisher_homepage',
            name='cataloghomepage',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.cataloghomepage'),
        ),
        migrations.AddField(
            model_name='historicaldatasetpublisher_homepage',
            name='datasetpublisher',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datasetpublisher'),
        ),
        migrations.AddField(
            model_name='historicaldatasetpublisher_homepage',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldatasetpublisher'),
        ),
        migrations.AddField(
            model_name='historicaldatasetpublisher',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldatasetpublisher',
            name='system_creator',
            field=models.ForeignKey(blank=True, db_constraint=False, editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldataset_theme',
            name='dataset',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_theme',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_theme',
            name='theme',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.theme'),
        ),
        migrations.AddField(
            model_name='historicaldataset_other_identifiers',
            name='dataset',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_other_identifiers',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_other_identifiers',
            name='otheridentifier',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.otheridentifier'),
        ),
        migrations.AddField(
            model_name='historicaldataset_language',
            name='dataset',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_language',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_language',
            name='language',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.language'),
        ),
        migrations.AddField(
            model_name='historicaldataset_infrastructure',
            name='dataset',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_infrastructure',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_infrastructure',
            name='researchinfra',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.researchinfra'),
        ),
        migrations.AddField(
            model_name='historicaldataset_field_of_science',
            name='dataset',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset_field_of_science',
            name='fieldofscience',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.fieldofscience'),
        ),
        migrations.AddField(
            model_name='historicaldataset_field_of_science',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='access_rights',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.accessrights'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='data_catalog',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datacatalog'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='dataset_versions',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datasetversions'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='draft_of',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='metadata_owner',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.metadataprovider'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='preservation',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.preservation'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='system_creator',
            field=models.ForeignKey(blank=True, db_constraint=False, editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldatacatalog_language',
            name='datacatalog',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datacatalog'),
        ),
        migrations.AddField(
            model_name='historicaldatacatalog_language',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicaldatacatalog'),
        ),
        migrations.AddField(
            model_name='historicaldatacatalog_language',
            name='language',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.language'),
        ),
        migrations.AddField(
            model_name='historicaldatacatalog',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldatacatalog',
            name='publisher',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datasetpublisher'),
        ),
        migrations.AddField(
            model_name='historicaldatacatalog',
            name='system_creator',
            field=models.ForeignKey(blank=True, db_constraint=False, editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='system_creator',
            field=models.ForeignKey(blank=True, db_constraint=False, editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalcataloghomepage',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalcataloghomepage',
            name='system_creator',
            field=models.ForeignKey(blank=True, db_constraint=False, editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalaccessrights_license',
            name='accessrights',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.accessrights'),
        ),
        migrations.AddField(
            model_name='historicalaccessrights_license',
            name='datasetlicense',
            field=models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.datasetlicense'),
        ),
        migrations.AddField(
            model_name='historicalaccessrights_license',
            name='history',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='core.historicalaccessrights'),
        ),
        migrations.AddField(
            model_name='historicalaccessrights',
            name='access_type',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.accesstype'),
        ),
        migrations.AddField(
            model_name='historicalaccessrights',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalaccessrights',
            name='system_creator',
            field=models.ForeignKey(blank=True, db_constraint=False, editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='funding',
            name='funder',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funding', to='core.funder'),
        ),
        migrations.AddField(
            model_name='funding',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='funder',
            name='funder_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refdata.fundertype'),
        ),
        migrations.AddField(
            model_name='funder',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agencies', to='actors.organization'),
        ),
        migrations.AddField(
            model_name='funder',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='filesetfilemetadata',
            name='file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dataset_metadata', to='files.file'),
        ),
        migrations.AddField(
            model_name='filesetfilemetadata',
            name='file_set',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='file_metadata', to='core.fileset'),
        ),
        migrations.AddField(
            model_name='filesetfilemetadata',
            name='file_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.filetype'),
        ),
        migrations.AddField(
            model_name='filesetfilemetadata',
            name='use_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usecategory'),
        ),
        migrations.AddField(
            model_name='filesetdirectorymetadata',
            name='file_set',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='directory_metadata', to='core.fileset'),
        ),
        migrations.AddField(
            model_name='filesetdirectorymetadata',
            name='storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.filestorage'),
        ),
        migrations.AddField(
            model_name='filesetdirectorymetadata',
            name='use_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usecategory'),
        ),
        migrations.AddField(
            model_name='fileset',
            name='dataset',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='file_set', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='fileset',
            name='files',
            field=models.ManyToManyField(related_name='file_sets', to='files.file'),
        ),
        migrations.AddField(
            model_name='fileset',
            name='storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='file_sets', to='files.filestorage'),
        ),
        migrations.AddField(
            model_name='fileset',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='entityrelation',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='relation', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='entityrelation',
            name='entity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relation', to='core.entity'),
        ),
        migrations.AddField(
            model_name='entityrelation',
            name='relation_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.relationtype'),
        ),
        migrations.AddField(
            model_name='entityrelation',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='entity',
            name='provenance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='used_entity', to='core.provenance'),
        ),
        migrations.AddField(
            model_name='entity',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='entity',
            name='type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.resourcetype'),
        ),
        migrations.AddField(
            model_name='datasetversions',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='datasetpublisher',
            name='homepage',
            field=models.ManyToManyField(related_name='publishers', to='core.cataloghomepage'),
        ),
        migrations.AddField(
            model_name='datasetpublisher',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='funding',
            field=models.ManyToManyField(related_name='projects', to='core.funding'),
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='participating_organizations',
            field=models.ManyToManyField(related_name='projects', to='actors.organization'),
        ),
        migrations.AddField(
            model_name='datasetproject',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='datasetlicense',
            name='reference',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='refdata.license'),
        ),
        migrations.AddField(
            model_name='datasetlicense',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='datasetactor',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='actors', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='access_rights',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dataset', to='core.accessrights'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='data_catalog',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='records', to='core.datacatalog'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='dataset_versions',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='datasets', to='core.datasetversions'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='draft_of',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='next_draft', to='core.dataset'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='field_of_science',
            field=models.ManyToManyField(blank=True, limit_choices_to={'is_essential_choice': True}, related_name='datasets', to='core.fieldofscience'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='infrastructure',
            field=models.ManyToManyField(blank=True, related_name='datasets', to='core.researchinfra'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='language',
            field=models.ManyToManyField(blank=True, limit_choices_to={'is_essential_choice': True}, related_name='datasets', to='core.language'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='dataset',
            name='metadata_owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='core.metadataprovider'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='other_identifiers',
            field=models.ManyToManyField(blank=True, to='core.otheridentifier'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='preservation',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='record', to='core.preservation'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='dataset',
            name='theme',
            field=models.ManyToManyField(blank=True, limit_choices_to={'is_essential_choice': True}, related_name='datasets', to='core.theme'),
        ),
        migrations.AddField(
            model_name='datacatalog',
            name='dataset_groups_admin',
            field=models.ManyToManyField(blank=True, help_text='User groups that are allowed to update all datasets in catalog.', related_name='catalogs_admin_datasets', to='auth.group'),
        ),
        migrations.AddField(
            model_name='datacatalog',
            name='dataset_groups_create',
            field=models.ManyToManyField(blank=True, help_text='User groups that are allowed to create datasets in catalog.', related_name='catalogs_create_datasets', to='auth.group'),
        ),
        migrations.AddField(
            model_name='datacatalog',
            name='language',
            field=models.ManyToManyField(related_name='catalogs', to='core.language'),
        ),
        migrations.AddField(
            model_name='datacatalog',
            name='publisher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='catalogs', to='core.datasetpublisher'),
        ),
        migrations.AddField(
            model_name='datacatalog',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='contract',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cataloghomepage',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='accessrights',
            name='access_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='access_rights', to='core.accesstype'),
        ),
        migrations.AddField(
            model_name='accessrights',
            name='license',
            field=models.ManyToManyField(related_name='access_rights', to='core.datasetlicense'),
        ),
        migrations.AddField(
            model_name='accessrights',
            name='restriction_grounds',
            field=models.ManyToManyField(related_name='access_rights', to='core.restrictiongrounds'),
        ),
        migrations.AddField(
            model_name='accessrights',
            name='system_creator',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='preservation',
            constraint=models.CheckConstraint(check=models.Q(('state__lt', 0), ('contract_id__isnull', False), _connector='OR'), name='core_preservation_has_valid_contract'),
        ),
        migrations.AlterUniqueTogether(
            name='filesetfilemetadata',
            unique_together={('file_set', 'file')},
        ),
        migrations.AlterUniqueTogether(
            name='filesetdirectorymetadata',
            unique_together={('file_set', 'pathname')},
        ),
        migrations.AddIndex(
            model_name='datasetlicense',
            index=models.Index(fields=['custom_url'], name='core_datase_custom__ae10d6_idx'),
        ),
    ]
