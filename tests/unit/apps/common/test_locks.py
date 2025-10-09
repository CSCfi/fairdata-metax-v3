import pytest
from apps.common.locks import lock_timeout, get_lock_timeout


@pytest.mark.django_db
def test_lock_timeout():
    """Test that lock_timeout sets postgres lock_timeout and later reverts it."""
    original = get_lock_timeout()
    with lock_timeout(1):
        assert get_lock_timeout() == "1s"
        with lock_timeout(2):
            assert get_lock_timeout() == "2s"
            with lock_timeout(3.5):
                assert get_lock_timeout() == "3500ms"
            assert get_lock_timeout() == "2s"
        assert get_lock_timeout() == "1s"
    assert get_lock_timeout() == original
