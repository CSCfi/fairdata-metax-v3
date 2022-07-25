# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for metax_service.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

import pytest
import factory.random
import django
from django.conf import settings


@pytest.fixture(scope='session', autouse=True)
def faker_session_locale():
    return ['en_US']


@pytest.fixture(scope='session', autouse=True)
def faker_seed():
    return settings.FACTORY_BOY_RANDOM_SEED

def pytest_collection_modifyitems(items):
    """Pytest provided hook function

    Pytest hook docs: https://docs.pytest.org/en/latest/how-to/writing_hook_functions.html
    """
    django.setup()
    factory.random.reseed_random(settings.FACTORY_BOY_RANDOM_SEED)
    for item in items:
        if "create" in item.nodeid or "delete" in item.nodeid:
            # adds django_db marker on any test with 'create' or 'delete' on its name
            item.add_marker(pytest.mark.django_db)
        if "behave" in item.nodeid:
            item.add_marker(pytest.mark.behave)
            item.add_marker(pytest.mark.django_db)
        if "unit" in item.nodeid:
            item.add_marker("unit")
