import pytest
from django.test import Client

from logbook.models import IndoorAscent as Ascent, IndoorRoute as Route

from .helpers import get, post
from .test_log_ascent import add
from .test_session_detail import log_session


@pytest.fixture
def session(signed_in_client: Client) -> int:
    pk = log_session(signed_in_client)
    add(signed_in_client, pk)
    add(signed_in_client, pk, name="Other")
    return pk


@pytest.mark.django_db
def test_list_rows_show_the_ascent_count(signed_in_client: Client, session: int):
    log_session(signed_in_client)

    html = get(signed_in_client, "/").content.decode()

    assert '<td data-label="Ascents">2</td>' in html
    assert '<td data-label="Ascents">0</td>' in html


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
