from django.http import HttpResponse
from django.test import Client


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path)  # pyright: ignore[reportReturnType]


def test_home_page_shows_empty_state_when_there_are_no_sessions(signed_in_client):
    response = get(signed_in_client, "/")

    assert response.status_code == 200
    assert "No Sessions yet" in response.content.decode()
