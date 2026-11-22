import re

from django.test import Client

from .helpers import get, post, session_ids


def log_session(client: Client, **fields: str) -> int:
    data = {"date": "2026-11-20", "activity_type": "climbing", **fields}
    post(client, "/sessions/new/", data)
    return session_ids(client)[0]


def test_anonymous_user_is_redirected_to_login():
    response = Client().get("/sessions/1/")

    assert response.status_code == 302
    assert response["Location"].startswith("/login/")


def test_unknown_session_is_not_found(signed_in_client: Client):
    assert get(signed_in_client, "/sessions/999999/").status_code == 404


def test_list_rows_link_to_the_detail_page(signed_in_client: Client):
    pk = log_session(signed_in_client)

    html = get(signed_in_client, "/").content.decode()

    assert re.search(rf'href="/sessions/{pk}/"', html)


def test_detail_page_shows_the_sessions_fields(signed_in_client: Client):
    pk = log_session(
        signed_in_client,
        location="Depot Gym",
        duration_minutes="137",
        effort="7",
        notes="Felt strong on overhangs",
        indoor_outdoor="indoor",
    )

    response = get(signed_in_client, f"/sessions/{pk}/")
    html = response.content.decode()

    assert response.status_code == 200
    for expected in ("2026-11-20", "Climbing", "Depot Gym", "137", "7", "Indoor"):
        assert expected in html
    assert "Felt strong on overhangs" in html


def test_indoor_session_shows_an_empty_ascents_section(signed_in_client: Client):
    pk = log_session(signed_in_client, indoor_outdoor="indoor")

    html = get(signed_in_client, f"/sessions/{pk}/").content.decode()

    assert "Ascents" in html
    assert "No Ascents yet" in html


def test_outdoor_session_says_outdoor_ascents_are_not_available(
    signed_in_client: Client,
):
    pk = log_session(signed_in_client, indoor_outdoor="outdoor")

    html = get(signed_in_client, f"/sessions/{pk}/").content.decode()

    assert "Outdoor Ascents are not available yet" in html
    assert "No Ascents yet" not in html


def test_session_without_a_setting_prompts_to_set_it(signed_in_client: Client):
    pk = log_session(signed_in_client)

    html = get(signed_in_client, f"/sessions/{pk}/").content.decode()

    assert "Set this Session as indoor or outdoor" in html
    assert f'href="/sessions/{pk}/edit/"' in html
    assert "No Ascents yet" not in html
