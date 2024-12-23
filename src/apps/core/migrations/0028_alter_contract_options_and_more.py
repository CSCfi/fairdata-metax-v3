# Generated by Django 4.2.16 on 2024-10-16 10:10

from django.db import migrations, models
import django.db.migrations.operations.special
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid
import django.contrib.postgres.fields.hstore
import json

def gen_contract_ids(apps, schema_editor):
    """Generate identifier for all existing contracts.

    Only test contracts exist currently so it should be ok
    to have arbitrary identifiers.
    """
    model = apps.get_model("core.Contract")
    for contract in model.objects.all():
        contract.contract_identifier = str(uuid.uuid4())
        contract.save()

    history_model = apps.get_model("core.HistoricalContract")
    for contract in history_model.objects.all():
        contract.contract_identifier = str(uuid.uuid4())
        contract.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_dataset_pid_generated_by_fairdata_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='legacy_id',
            field=models.BigIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='legacy_id',
            field=models.BigIntegerField(null=True),
        ),
        migrations.AlterModelOptions(
            name='contract',
            options={},
        ),
        migrations.RemoveField(
            model_name='contract',
            name='url',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='valid_until',
        ),
        migrations.RemoveField(
            model_name='historicalcontract',
            name='url',
        ),
        migrations.RemoveField(
            model_name='historicalcontract',
            name='valid_until',
        ),
        migrations.AddField(
            model_name='contract',
            name='organization_identifier',
            field=models.CharField(blank=True, max_length=200, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contract',
            name='organization_name',
            field=models.CharField(blank=True, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contract',
            name='record_created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created'),
        ),
        migrations.AddField(
            model_name='contract',
            name='record_modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='contract',
            name='validity_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contract',
            name='validity_start_date',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='organization_identifier',
            field=models.CharField(default='', max_length=200, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='organization_name',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='record_created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created'),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='record_modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='validity_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='validity_start_date',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contract',
            name='created',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='contract',
            name='modified',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='historicalcontract',
            name='created',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='historicalcontract',
            name='modified',
            field=models.DateTimeField(),
        ),
        migrations.CreateModel(
            name='ContractService',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('identifier', models.CharField(max_length=64)),
                ('name', models.CharField(max_length=200)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_service', to='core.contract')),
            ],
        ),
        migrations.CreateModel(
            name='ContractContact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField()),
                ('phone', models.CharField(blank=True, max_length=64)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact', to='core.contract')),
            ],
        ),
        migrations.AddField(
            model_name='contract',
            name='contract_identifier',
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='contract_identifier',
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.RunPython(gen_contract_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contract',
            name='contract_identifier',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='historicalcontract',
            name='contract_identifier',
            field=models.CharField(max_length=64),
        ),
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.UniqueConstraint(condition=models.Q(('removed__isnull', True)), fields=('contract_identifier',), name='core_contract_unique_contract_identifier'),
        ),
        migrations.RemoveField(
            model_name='contract',
            name='description',
        ),
        migrations.RemoveField(
            model_name='historicalcontract',
            name='description',
        ),
        migrations.AddField(
            model_name='contract',
            name='description',
            field=django.contrib.postgres.fields.hstore.HStoreField(blank=True, help_text='example: {"en":"description", "fi":"kuvaus"}', null=True),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='description',
            field=django.contrib.postgres.fields.hstore.HStoreField(blank=True, help_text='example: {"en":"description", "fi":"kuvaus"}', null=True),
        ),
        migrations.AlterModelOptions(
            name='contract',
            options={'ordering': ['record_created', 'id']},
        ),
        migrations.AlterModelOptions(
            name='contractcontact',
            options={'ordering': ['name', 'email', 'id']},
        ),
        migrations.AlterModelOptions(
            name='contractservice',
            options={'ordering': ['name', 'identifier']},
        ),
        migrations.AlterField(
            model_name='contract',
            name='organization_name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='historicalcontract',
            name='organization_identifier',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
