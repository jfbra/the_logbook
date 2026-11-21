from django.test import Client

from .helpers import get


def test_home_page_shows_empty_state_when_there_are_no_sessions(
    signed_in_client: Client,
):
    response = get(signed_in_client, "/")

    assert response.status_code == 200
    assert "No Sessions yet" in response.content.decode()
