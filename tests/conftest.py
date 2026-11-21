import pytest
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("athlete", password="correct-horse")


@pytest.fixture
def signed_in_client(user) -> Client:
    client = Client()
    client.force_login(user)
    return client
