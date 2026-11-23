import pytest
from django.test import Client

from logbook.models import IndoorAscent as Ascent, IndoorRoute as Route, Session

from .helpers import get, post
from .test_log_ascent import add
from .test_session_detail import log_session


@pytest.fixture
def session(signed_in_client: Client) -> int:
    return log_session(signed_in_client, indoor_outdoor="indoor", location="Depot")


def dogged_rope(client: Client, pk: int) -> Ascent:
    add(
        client,
        pk,
        name="Rope",
        route_type="sport",
        discipline="top_rope",
        result="dogged",
        rests="2",
    )
    return Ascent.objects.get()


def test_anonymous_user_is_redirected_to_login():
    assert Client().get("/ascents/1/edit/")["Location"].startswith("/login/")
    assert Client().post("/ascents/1/delete/")["Location"].startswith("/login/")


def test_unknown_ascent_is_not_found(signed_in_client: Client):
    assert get(signed_in_client, "/ascents/999999/edit/").status_code == 404
    assert get(signed_in_client, "/ascents/999999/delete/").status_code == 404


@pytest.mark.django_db
def test_session_page_links_to_edit(signed_in_client: Client, session: int):
    ascent = dogged_rope(signed_in_client, session)

    html = get(signed_in_client, f"/sessions/{session}/").content.decode()

    assert f'href="/ascents/{ascent.pk}/edit/"' in html


@pytest.mark.django_db
def test_edit_changes_discipline_rests_and_notes(
    signed_in_client: Client, session: int
):
    ascent = dogged_rope(signed_in_client, session)

    response = post(
        signed_in_client,
        f"/ascents/{ascent.pk}/edit/",
        {"discipline": "sport", "result": "dogged", "rests": "4", "notes": "better"},
    )
    ascent.refresh_from_db()

    assert response.status_code == 302
    assert response["Location"] == f"/sessions/{session}/"
    assert (ascent.discipline, ascent.rests, ascent.notes) == ("sport", 4, "better")


@pytest.mark.django_db
def test_edit_form_only_offers_disciplines_for_the_route_type(
    signed_in_client: Client, session: int
):
    ascent = dogged_rope(signed_in_client, session)

    html = get(signed_in_client, f"/ascents/{ascent.pk}/edit/").content.decode()

    assert 'value="sport"' in html
    assert 'value="boulder"' not in html


@pytest.mark.django_db
def test_discipline_change_that_invalidates_the_result_needs_a_new_result(
    signed_in_client: Client, session: int
):
    add(
        signed_in_client,
        session,
        name="Rope",
        route_type="sport",
        discipline="sport",
        result="redpoint",
    )
    ascent = Ascent.objects.get()

    response = post(
        signed_in_client,
        f"/ascents/{ascent.pk}/edit/",
        {"discipline": "top_rope", "result": "redpoint"},
    )
    ascent.refresh_from_db()

    assert response.status_code == 200
    assert "is not a result for" in response.content.decode()
    assert (ascent.discipline, ascent.result) == ("sport", "redpoint")


@pytest.mark.django_db
def test_rests_are_cleared_when_result_is_no_longer_dogged(
    signed_in_client: Client, session: int
):
    ascent = dogged_rope(signed_in_client, session)

    post(
        signed_in_client,
        f"/ascents/{ascent.pk}/edit/",
        {"discipline": "top_rope", "result": "onsight", "rests": "2"},
    )
    ascent.refresh_from_db()

    assert (ascent.result, ascent.rests) == ("onsight", None)


@pytest.mark.django_db
@pytest.mark.parametrize("rests", ["0", "-1", "1.5"])
def test_edit_rejects_bad_rests(signed_in_client: Client, session: int, rests: str):
    ascent = dogged_rope(signed_in_client, session)

    response = post(
        signed_in_client,
        f"/ascents/{ascent.pk}/edit/",
        {"discipline": "top_rope", "result": "dogged", "rests": rests},
    )
    ascent.refresh_from_db()

    assert response.status_code == 200
    assert ascent.rests == 2


@pytest.mark.django_db
def test_delete_asks_for_confirmation_first(signed_in_client: Client, session: int):
    ascent = dogged_rope(signed_in_client, session)

    response = get(signed_in_client, f"/ascents/{ascent.pk}/delete/")

    assert response.status_code == 200
    assert "Delete this Ascent?" in response.content.decode()
    assert Ascent.objects.count() == 1


@pytest.mark.django_db
def test_confirmed_delete_removes_the_ascent_but_keeps_the_route(
    signed_in_client: Client, session: int
):
    ascent = dogged_rope(signed_in_client, session)

    response = post(signed_in_client, f"/ascents/{ascent.pk}/delete/")

    assert response["Location"] == f"/sessions/{session}/"
    assert Ascent.objects.count() == 0
    assert Route.objects.count() == 1


@pytest.mark.django_db
def test_editing_an_ascent_on_a_non_indoor_session_is_not_found(
    signed_in_client: Client, session: int
):
    ascent = dogged_rope(signed_in_client, session)
    Session.objects.filter(pk=session).update(indoor_outdoor="outdoor")

    response = post(
        signed_in_client,
        f"/ascents/{ascent.pk}/edit/",
        {"discipline": "sport", "result": "dogged"},
    )

    assert response.status_code == 404
