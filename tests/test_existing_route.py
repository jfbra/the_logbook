import re

import pytest
from django.test import Client

from logbook.models import Ascent, Route

from .helpers import get, post
from .test_log_ascent import add
from .test_session_detail import log_session


@pytest.fixture
def indoor(signed_in_client: Client) -> int:
    return log_session(signed_in_client, indoor_outdoor="indoor", location="Depot")


def search(client: Client, pk: int, name: str) -> str:
    return get(client, f"/sessions/{pk}/routes/search/?name={name}").content.decode()


@pytest.mark.django_db
def test_search_lists_matching_routes_ignoring_case(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave", grade="V4", result="send")

    html = search(signed_in_client, indoor, "cave")

    assert "Blue Cave" in html
    assert "V4" in html
    assert "last: Send" in html


@pytest.mark.django_db
def test_search_only_covers_the_sessions_location(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")
    elsewhere = log_session(signed_in_client, indoor_outdoor="indoor", location="Other")
    add(signed_in_client, elsewhere, name="Blue Overhang")

    html = search(signed_in_client, indoor, "blue")

    assert "Blue Cave" in html
    assert "Blue Overhang" not in html


@pytest.mark.django_db
def test_search_rejects_non_indoor_sessions(signed_in_client: Client):
    pk = log_session(signed_in_client, indoor_outdoor="outdoor")

    assert (
        get(signed_in_client, f"/sessions/{pk}/routes/search/?name=a").status_code
        == 404
    )


@pytest.mark.django_db
def test_choosing_a_route_logs_an_ascent_without_a_duplicate(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")
    route = Route.objects.get()

    post(
        signed_in_client,
        f"/sessions/{indoor}/ascents/new/",
        {"route": str(route.pk), "discipline": "boulder", "result": "repeat"},
    )

    assert Route.objects.count() == 1
    assert Ascent.objects.filter(route=route).count() == 2


@pytest.mark.django_db
def test_new_route_with_an_existing_name_reuses_it_ignoring_case(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")

    add(signed_in_client, indoor, name="  blue CAVE ", result="send")

    assert Route.objects.count() == 1
    assert Ascent.objects.count() == 2


@pytest.mark.django_db
def test_same_name_at_another_location_is_a_different_route(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")
    elsewhere = log_session(signed_in_client, indoor_outdoor="indoor", location="Other")

    add(signed_in_client, elsewhere, name="Blue Cave")

    assert Route.objects.count() == 2


@pytest.mark.django_db
def test_chosen_route_form_offers_only_disciplines_for_its_type(
    signed_in_client: Client, indoor: int
):
    add(
        signed_in_client,
        indoor,
        name="Rope",
        route_type="roped",
        discipline="sport",
        result="onsight",
    )
    route = Route.objects.get()

    html = get(
        signed_in_client, f"/sessions/{indoor}/ascents/form/?route={route.pk}"
    ).content.decode()

    assert 'value="top_rope"' in html
    assert 'value="sport"' in html
    assert 'value="boulder"' not in html
    assert "Rope" in html


@pytest.mark.django_db
def test_chosen_route_rejects_a_discipline_that_does_not_suit_it(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")
    route = Route.objects.get()

    response = post(
        signed_in_client,
        f"/sessions/{indoor}/ascents/new/",
        {"route": str(route.pk), "discipline": "sport", "result": "onsight"},
    )

    assert response.status_code == 422
    assert Ascent.objects.count() == 1


@pytest.mark.django_db
def test_a_route_from_another_location_cannot_be_chosen(
    signed_in_client: Client, indoor: int
):
    elsewhere = log_session(signed_in_client, indoor_outdoor="indoor", location="Other")
    add(signed_in_client, elsewhere, name="Far Route")
    route = Route.objects.get()

    response = post(
        signed_in_client,
        f"/sessions/{indoor}/ascents/new/",
        {"route": str(route.pk), "discipline": "boulder", "result": "send"},
    )

    assert response.status_code == 422
    assert Ascent.objects.count() == 1


def test_new_route_form_wires_up_the_search(signed_in_client: Client, indoor: int):
    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    assert re.search(rf'hx-get="/sessions/{indoor}/routes/search/"', html)


@pytest.mark.django_db
def test_non_ascii_digit_route_ids_do_not_crash(signed_in_client: Client, indoor: int):
    assert (
        get(
            signed_in_client, f"/sessions/{indoor}/ascents/form/?route=%C2%B2"
        ).status_code
        == 200
    )
    response = post(
        signed_in_client,
        f"/sessions/{indoor}/ascents/new/",
        {"route": "²", "discipline": "boulder", "result": "send"},
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_reusing_a_name_with_a_different_type_is_rejected(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Slab")

    response = add(
        signed_in_client,
        indoor,
        name="blue slab",
        route_type="roped",
        discipline="sport",
        result="onsight",
    )

    assert response.status_code == 422
    assert "already exists here as a boulder" in response.content.decode()
    assert Ascent.objects.count() == 1
