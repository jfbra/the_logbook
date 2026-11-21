from django.test import Client

from .helpers import get, post, session_ids


def log(client: Client, **fields: str) -> int:
    data = {"date": "2026-11-20", "activity_type": "climbing", **fields}
    post(client, "/sessions/new/", data)
    return session_ids(client)[0]


def edit_form(**overrides: str) -> dict[str, str]:
    return {"date": "2026-11-20", "activity_type": "climbing", **overrides}


def test_edit_form_is_prefilled_with_the_sessions_values(signed_in_client: Client):
    pk = log(signed_in_client, location="Oldplace", duration_minutes="60")

    response = get(signed_in_client, f"/sessions/{pk}/edit/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Oldplace" in html
    assert 'value="60"' in html


def test_editing_a_session_changes_what_the_list_shows(signed_in_client: Client):
    pk = log(signed_in_client, location="Oldplace", duration_minutes="60")

    response = post(
        signed_in_client,
        f"/sessions/{pk}/edit/",
        edit_form(location="Newplace", duration_minutes="75"),
    )

    assert response["Location"] == "/"
    html = get(signed_in_client, "/").content.decode()
    assert "Newplace" in html
    assert "75" in html
    assert "Oldplace" not in html
    assert len(session_ids(signed_in_client)) == 1


def test_edits_are_validated_like_creation(signed_in_client: Client):
    pk = log(signed_in_client, location="Keepme", effort="5")

    for bad in [
        edit_form(date="", location="Changed"),
        edit_form(activity_type="", location="Changed"),
        edit_form(effort="11", location="Changed"),
        edit_form(effort="0", location="Changed"),
    ]:
        response = post(signed_in_client, f"/sessions/{pk}/edit/", bad)
        assert response.status_code == 200

    html = get(signed_in_client, "/").content.decode()
    assert "Keepme" in html
    assert "Changed" not in html


def test_editing_a_missing_session_is_not_found(signed_in_client: Client):
    assert get(signed_in_client, "/sessions/99999/edit/").status_code == 404
    assert get(signed_in_client, "/sessions/99999/delete/").status_code == 404


def test_delete_asks_for_confirmation_and_does_not_delete_on_view(
    signed_in_client: Client,
):
    pk = log(signed_in_client, location="Keepme")

    response = get(signed_in_client, f"/sessions/{pk}/delete/")

    assert response.status_code == 200
    assert "Keepme" in response.content.decode()
    assert session_ids(signed_in_client) == [pk]


def test_confirming_delete_removes_the_session(signed_in_client: Client):
    pk = log(signed_in_client, location="Goner")

    response = post(signed_in_client, f"/sessions/{pk}/delete/")

    assert response["Location"] == "/"
    html = get(signed_in_client, "/").content.decode()
    assert "Goner" not in html
    assert "No Sessions yet" in html


def test_cancelling_delete_keeps_the_session(signed_in_client: Client):
    pk = log(signed_in_client, location="Keepme")
    confirm = get(signed_in_client, f"/sessions/{pk}/delete/").content.decode()

    assert 'href="/"' in confirm  # the cancel link goes back to the list
    assert "Keepme" in get(signed_in_client, "/").content.decode()


def test_edit_and_delete_require_login(signed_in_client: Client, db):
    pk = log(signed_in_client)
    anon = Client()

    assert get(anon, f"/sessions/{pk}/edit/").status_code == 302
    assert post(anon, f"/sessions/{pk}/delete/").status_code == 302
    assert session_ids(signed_in_client) == [pk]
