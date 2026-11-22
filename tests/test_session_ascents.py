import pytest
from django.test import Client

from logbook.models import Ascent, Route

from .helpers import get, post
from .test_log_ascent import add
from .test_session_detail import log_session


@pytest.fixture
def session(signed_in_client: Client) -> int:
    pk = log_session(signed_in_client, indoor_outdoor="indoor", location="Depot")
    add(signed_in_client, pk)
    add(signed_in_client, pk, name="Other")
    return pk


def edit(client: Client, pk: int, setting: str):
    return post(
        client,
        f"/sessions/{pk}/edit/",
        {"date": "2026-11-20", "activity_type": "climbing", "location": "Depot",
         "indoor_outdoor": setting},
    )  # fmt: skip


@pytest.mark.django_db
def test_list_rows_show_the_ascent_count(signed_in_client: Client, session: int):
    log_session(signed_in_client, indoor_outdoor="indoor")

    html = get(signed_in_client, "/").content.decode()

    assert '<td data-label="Ascents">2</td>' in html
    assert '<td data-label="Ascents">0</td>' in html


@pytest.mark.django_db
@pytest.mark.parametrize("setting", ["outdoor", ""])
def test_changing_the_setting_is_rejected_once_ascents_exist(
    signed_in_client: Client, session: int, setting: str
):
    response = edit(signed_in_client, session, setting)

    assert response.status_code == 200
    assert (
        "cannot be changed because this Session has 2 Ascents"
        in response.content.decode()
    )


@pytest.mark.django_db
def test_keeping_the_setting_is_still_allowed(signed_in_client: Client, session: int):
    assert edit(signed_in_client, session, "indoor").status_code == 302


@pytest.mark.django_db
def test_setting_can_change_when_there_are_no_ascents(signed_in_client: Client):
    pk = log_session(signed_in_client, indoor_outdoor="indoor")

    assert edit(signed_in_client, pk, "outdoor").status_code == 302


@pytest.mark.django_db
def test_delete_confirmation_states_the_ascent_count(
    signed_in_client: Client, session: int
):
    html = get(signed_in_client, f"/sessions/{session}/delete/").content.decode()

    assert "2 Ascents" in html


@pytest.mark.django_db
def test_deleting_a_session_deletes_its_ascents_but_not_routes(
    signed_in_client: Client, session: int
):
    post(signed_in_client, f"/sessions/{session}/delete/")

    assert Ascent.objects.count() == 0
    assert Route.objects.count() == 2
