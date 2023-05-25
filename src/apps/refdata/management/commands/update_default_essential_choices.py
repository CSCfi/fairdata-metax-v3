import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.refdata.models import FieldOfScience, Language, Theme

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        langs = Language.available_objects.filter(
            url__in=settings.ESSENTIAL_LANGUAGE_CHOICE_URLS
        ).update(is_essential_choice=True)
        fields_of_science = FieldOfScience.available_objects.filter(
            url__in=settings.ESSENTIAL_FIELD_OF_SCIENCE_CHOICE_URLS
        ).update(is_essential_choice=True)
        themes = Theme.available_objects.filter(
            url__in=settings.ESSENTIAL_THEME_CHOICE_URLS
        ).update(is_essential_choice=True)
        logger.info(f"Following updates were made {langs=}, {fields_of_science=}, {themes=}")
        self.stdout.write("default essentials updated successfully")
