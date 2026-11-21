from django.http import HttpResponse
from django.test import Client


def post(client: Client, path: str, data: dict[str, str] | None = None) -> HttpResponse:
    return client.post(path, data or {})  # pyright: ignore[reportReturnType]


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path)  # pyright: ignore[reportReturnType]


def test_anonymous_home_request_redirects_to_login(db):
    response = get(Client(), "/")

    assert response.status_code == 302
    assert response["Location"].startswith("/login/")


def test_login_page_renders_for_anonymous_visitors(db):
    assert get(Client(), "/login/").status_code == 200


def test_valid_credentials_sign_in_and_show_home_page(user):
    client = Client()

    response = post(
        client, "/login/", {"username": "athlete", "password": "correct-horse"}
    )

    assert response.status_code == 302
    assert get(client, "/").status_code == 200


def test_invalid_credentials_are_rejected_with_a_message(user):
    client = Client()

    response = post(client, "/login/", {"username": "athlete", "password": "wrong"})

    assert response.status_code == 200
    assert "Please enter a correct username and password" in response.content.decode()
    assert get(client, "/").status_code == 302


def test_signing_out_returns_to_login_and_locks_protected_pages(signed_in_client):
    response = post(signed_in_client, "/logout/")

    assert response.status_code == 302
    assert response["Location"].startswith("/login/")
    assert get(signed_in_client, "/").status_code == 302
