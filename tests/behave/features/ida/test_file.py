import pytest
from pytest_bdd import scenario


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario('file.feature', 'IDA User freezes files')
def test_file_freeze():
    assert True


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario('file.feature', 'IDA user unfreezes files')
def test_file_unfreeze():
    assert True
