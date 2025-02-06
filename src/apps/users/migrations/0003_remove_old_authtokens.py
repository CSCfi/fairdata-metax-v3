# Generated by Django 4.2.17 on 2025-02-06 07:43

from django.db import migrations
from django.db.models.functions import Length


def remove_old_tokens(apps, schema_editor):
    """Remove old tokens obsoleted by django-rest-knox 5.0."""
    model = apps.get_model("knox", "AuthToken")

    # Old tokens have token_key length 8
    old_tokens = model.objects.alias(key_length=Length('token_key')).filter(key_length=8)
    old_tokens.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_remove_metaxuser_is_removed_metaxuser_removed'),
        ('knox', '0009_extend_authtoken_field')
    ]

    operations = [
        migrations.RunPython(remove_old_tokens, migrations.RunPython.noop)
    ]
