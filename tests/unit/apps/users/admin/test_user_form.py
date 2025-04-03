import pytest
from django.contrib.admin.sites import AdminSite

from apps.users.forms import OptionalPasswordUserCreationForm

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


def test_user_create_form():
    form = OptionalPasswordUserCreationForm(
        data={
            "username": "hello",
            "password1": "someval1dPASsword",
            "password2": "someval1dPASsword",
        }
    )
    assert form.is_valid()
    user = form.save()
    assert user.username == "hello"
    assert user.check_password("someval1dPASsword")


def test_user_create_form_mismatching_password():
    form = OptionalPasswordUserCreationForm(
        data={
            "username": "hello",
            "password1": "someval1dPASsword",
            "password2": "wrong",
        }
    )
    assert not form.is_valid()

def test_user_create_form_no_password():
    form = OptionalPasswordUserCreationForm(
        data={
            "username": "hello",
            "password1": "",
            "password2": "",
        }
    )
    assert form.is_valid()
    user = form.save()
    assert user.check_password("") is False

