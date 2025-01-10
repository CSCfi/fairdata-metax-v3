import logging
from sre_constants import SUCCESS

import pytest

from apps.users.models import MetaxUser

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_user_soft_delete(user):
    user.delete()
    searched_user = MetaxUser.objects.get(username=user.username)
    assert searched_user.removed is not None


@pytest.mark.django_db
def test_user_undelete(user):
    """When using undelete method

    Metax user should return to available objects
    is_hidden param should set to False by default
    """
    user.is_hidden = True
    user.save()
    user.undelete()
    searched_user = MetaxUser.available_objects.get(username=user.username)
    assert searched_user.removed is None
    assert searched_user.is_hidden is False


@pytest.mark.django_db
def test_user_hard_delete(user):
    user.delete(soft=False)
    users = MetaxUser.objects.all()

    # check if metax technical user is created on other tests
    if len(users) == 1:
        assert MetaxUser.objects.all()[0].username == "metax"
