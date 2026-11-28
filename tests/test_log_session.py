from django.test import Client
from django.utils import timezone

from .helpers import get, post


def valid_form(**overrides: str) -> dict[str, str]:
    data = {"date": "2026-11-20"}
    data.update(overrides)
    return data


def test_new_session_form_defaults_date_to_today(
    signed_in_client: Client,
):
    response = get(signed_in_client, "/sessions/new/")
    html = response.content.decode()

    assert response.status_code == 200
    assert f'value="{timezone.localdate().isoformat()}"' in html


def test_valid_session_redirects_to_list_and_appears_there(signed_in_client: Client):
    response = post(
        signed_in_client,
        "/sessions/new/",
        valid_form(
            duration_minutes="90",
            effort="7",
            notes="Felt strong",
        ),
    )

    assert response.status_code == 302
    assert response["Location"] == "/"
    html = get(signed_in_client, "/").content.decode()
    assert "No Sessions yet" not in html
    for expected in ["2026-11-20", "90", "7"]:
        assert expected in html


def test_optional_fields_can_be_left_blank(signed_in_client: Client):
    response = post(signed_in_client, "/sessions/new/", valid_form())

    assert response.status_code == 302
    assert "No Sessions yet" not in get(signed_in_client, "/").content.decode()


def test_missing_date_is_rejected_and_nothing_is_saved(signed_in_client: Client):
    response = post(signed_in_client, "/sessions/new/", valid_form(date=""))

    assert response.status_code == 200
    assert "This field is required" in response.content.decode()
    assert "No Sessions yet" in get(signed_in_client, "/").content.decode()


def test_effort_outside_one_to_ten_is_rejected(signed_in_client: Client):
    for bad in ["0", "11"]:
        response = post(signed_in_client, "/sessions/new/", valid_form(effort=bad))

        assert response.status_code == 200
    assert "No Sessions yet" in get(signed_in_client, "/").content.decode()


def test_effort_of_one_and_ten_are_accepted(signed_in_client: Client):
    for ok in ["1", "10"]:
        assert (
            post(signed_in_client, "/sessions/new/", valid_form(effort=ok)).status_code
            == 302
        )


def test_sessions_are_listed_newest_first(signed_in_client: Client):
    for day in ["2026-11-10", "2026-11-20", "2026-11-15"]:
        post(signed_in_client, "/sessions/new/", valid_form(date=day))

    html = get(signed_in_client, "/").content.decode()

    assert (
        html.index("2026-11-20") < html.index("2026-11-15") < html.index("2026-11-10")
    )


def test_session_pages_require_login(db):
    assert get(Client(), "/sessions/new/").status_code == 302
