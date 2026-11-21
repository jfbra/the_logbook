from django.test import Client

from .helpers import get, post


def test_anonymous_home_request_redirects_to_login(db):
    response = get(Client(), "/")

    assert response.status_code == 302
    assert response["Location"] == "/login/?next=/"


def test_login_page_renders_for_anonymous_visitors(db):
    assert get(Client(), "/login/").status_code == 200


def test_valid_credentials_sign_in_and_show_home_page(user, credentials):
    client = Client()

    response = post(client, "/login/", credentials)

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert get(client, "/").status_code == 200


def test_invalid_credentials_are_rejected_with_a_message(user, credentials):
    client = Client()

    response = post(client, "/login/", {**credentials, "password": "wrong"})

    assert response.status_code == 200
    assert "Please enter a correct username and password" in response.content.decode()
    assert get(client, "/").status_code == 302


def test_signing_out_returns_to_login_and_locks_protected_pages(signed_in_client):
    response = post(signed_in_client, "/logout/")

    assert response.status_code == 302
    assert response["Location"] == "/login/"
    assert get(signed_in_client, "/login/").status_code == 200
    assert get(signed_in_client, "/").status_code == 302


def test_logout_requires_post(signed_in_client):
    assert get(signed_in_client, "/logout/").status_code == 405
    assert get(signed_in_client, "/").status_code == 200
