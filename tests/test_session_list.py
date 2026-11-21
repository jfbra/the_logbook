from django.http import HttpResponse
from django.test import Client


def test_home_page_shows_empty_state_when_there_are_no_sessions(db):
    response: HttpResponse = Client().get("/")  # pyright: ignore[reportAssignmentType]

    assert response.status_code == 200
    assert "No Sessions yet" in response.content.decode()
