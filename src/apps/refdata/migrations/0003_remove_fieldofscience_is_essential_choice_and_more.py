# Generated by Django 4.2.11 on 2024-07-31 08:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('refdata', '0002_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fieldofscience',
            name='is_essential_choice',
        ),
        migrations.RemoveField(
            model_name='language',
            name='is_essential_choice',
        ),
        migrations.RemoveField(
            model_name='theme',
            name='is_essential_choice',
        ),
    ]