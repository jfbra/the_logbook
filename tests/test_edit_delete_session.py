from django.test import Client

from .helpers import get, post, session_ids


def session_form(**fields: str) -> dict[str, str]:
    return {"date": "2026-11-20", **fields}


def log_session(client: Client, **fields: str) -> int:
    post(client, "/sessions/new/", session_form(**fields))
    return session_ids(client)[0]


def test_edit_form_is_prefilled_with_the_sessions_values(signed_in_client: Client):
    pk = log_session(signed_in_client, notes="Oldplace", duration_minutes="137")

    response = get(signed_in_client, f"/sessions/{pk}/edit/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Oldplace" in html
    assert "137" in html


def test_editing_a_session_changes_what_the_list_shows(signed_in_client: Client):
    pk = log_session(signed_in_client, notes="Oldplace", duration_minutes="137")

    response = post(
        signed_in_client,
        f"/sessions/{pk}/edit/",
        session_form(notes="Newplace", duration_minutes="251"),
    )

    assert response["Location"] == "/"
    html = get(signed_in_client, "/").content.decode()
    assert "251" in html
    assert "137" not in html
    assert len(session_ids(signed_in_client)) == 1
    detail = get(signed_in_client, f"/sessions/{pk}/").content.decode()
    assert "Newplace" in detail
    assert "Oldplace" not in detail


def test_edits_are_validated_like_creation(signed_in_client: Client):
    pk = log_session(signed_in_client, notes="Keepme", effort="5")

    for bad in [
        session_form(date="", notes="Changed"),
        session_form(effort="11", notes="Changed"),
        session_form(effort="0", notes="Changed"),
    ]:
        response = post(signed_in_client, f"/sessions/{pk}/edit/", bad)
        assert response.status_code == 200
        assert "errorlist" in response.content.decode()

    html = get(signed_in_client, f"/sessions/{pk}/").content.decode()
    assert "Keepme" in html
    assert "Changed" not in html


def test_editing_a_missing_session_is_not_found(signed_in_client: Client):
    assert get(signed_in_client, "/sessions/99999/edit/").status_code == 404
    assert get(signed_in_client, "/sessions/99999/delete/").status_code == 404


def test_delete_asks_for_confirmation_and_does_not_delete_on_view(
    signed_in_client: Client,
):
    pk = log_session(signed_in_client, notes="Keepme")

    response = get(signed_in_client, f"/sessions/{pk}/delete/")

    assert response.status_code == 200
    assert "2026-11-20" in response.content.decode()
    assert session_ids(signed_in_client) == [pk]


def test_confirming_delete_removes_the_session(signed_in_client: Client):
    pk = log_session(signed_in_client, notes="Goner")

    response = post(signed_in_client, f"/sessions/{pk}/delete/")

    assert response["Location"] == "/"
    html = get(signed_in_client, "/").content.decode()
    assert "No Sessions yet" in html


def test_edit_and_delete_require_login(signed_in_client: Client):
    pk = log_session(signed_in_client)
    anon = Client()

    assert get(anon, f"/sessions/{pk}/edit/")["Location"].startswith("/login/")
    assert post(anon, f"/sessions/{pk}/delete/").status_code == 302
    assert session_ids(signed_in_client) == [pk]
