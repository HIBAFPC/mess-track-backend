import pytest


@pytest.mark.django_db
def test_sanity():
    assert 1 + 1 == 2


@pytest.mark.django_db
def test_user_count():
    from apps.accounts.models import User

    assert User.objects.count() == 0
