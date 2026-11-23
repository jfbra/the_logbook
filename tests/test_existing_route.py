import re

import pytest
from django.test import Client

from logbook.models import Gym, IndoorAscent as Ascent, IndoorRoute as Route

from .helpers import get, post
from .test_log_ascent import add
from .test_session_detail import log_session


@pytest.fixture
def indoor(signed_in_client: Client) -> int:
    return log_session(signed_in_client, indoor_outdoor="indoor")


def search(client: Client, pk: int, name: str, gym: str = "Depot") -> str:
    return get(
        client, f"/sessions/{pk}/routes/search/?gym={gym}&name={name}"
    ).content.decode()


@pytest.mark.django_db
def test_search_lists_matching_routes_ignoring_case(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave", grade="V4", result="tick")
    Route.objects.update(hold_colour="blue", date_set="2026-10-01")

    html = search(signed_in_client, indoor, "cave", gym="depot")

    assert "Blue Cave" in html
    assert "V4" in html
    assert "blue" in html
    assert "set 2026-10-01" in html
    assert "last: Tick" in html


@pytest.mark.django_db
def test_search_only_covers_the_chosen_gym(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor, name="Blue Cave")
    add(signed_in_client, indoor, name="Blue Overhang", gym="Other")

    html = search(signed_in_client, indoor, "blue")

    assert "Blue Cave" in html
    assert "Blue Overhang" not in html


@pytest.mark.django_db
def test_search_at_an_unknown_gym_finds_nothing(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor, name="Blue Cave")

    assert "Blue Cave" not in search(signed_in_client, indoor, "blue", gym="Nowhere")


@pytest.mark.django_db
def test_search_rejects_non_indoor_sessions(signed_in_client: Client):
    pk = log_session(signed_in_client, indoor_outdoor="outdoor")

    assert (
        get(signed_in_client, f"/sessions/{pk}/routes/search/?name=a").status_code
        == 404
    )


@pytest.mark.django_db
def test_a_new_gym_is_created_by_typing_its_name(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor, gym="  Brand New Gym ")

    assert Gym.objects.get().name == "Brand New Gym"


@pytest.mark.django_db
def test_an_existing_gym_is_reused_ignoring_case(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor, gym="Depot")
    add(signed_in_client, indoor, gym="  depot ", name="Other")

    assert Gym.objects.count() == 1
    assert Route.objects.count() == 2


@pytest.mark.django_db
def test_a_rejected_ascent_does_not_create_the_gym(
    signed_in_client: Client, indoor: int
):
    response = add(signed_in_client, indoor, gym="Ghost", grade="")

    assert response.status_code == 422
    assert not Gym.objects.exists()


@pytest.mark.django_db
def test_gym_is_required_for_a_new_route(signed_in_client: Client, indoor: int):
    response = add(signed_in_client, indoor, gym=" ")

    assert response.status_code == 422
    assert not Route.objects.exists()


@pytest.mark.django_db
def test_two_routes_with_the_same_name_can_exist_at_one_gym(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")
    add(signed_in_client, indoor, name="blue cave")

    assert Route.objects.count() == 2
    assert Gym.objects.count() == 1


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
def test_chosen_route_form_offers_only_disciplines_for_its_type(
    signed_in_client: Client, indoor: int
):
    add(
        signed_in_client,
        indoor,
        name="Rope",
        route_type="sport",
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
    assert "Depot" in html


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


def test_new_route_form_wires_up_the_search(signed_in_client: Client, indoor: int):
    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    assert re.search(rf'hx-get="/sessions/{indoor}/routes/search/"', html)
    assert 'name="gym"' in html


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
        {"route": "²", "discipline": "boulder", "result": "tick"},
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_deleting_a_gym_that_has_routes_is_refused(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor)
    gym = Gym.objects.get()

    response = post(signed_in_client, f"/gyms/{gym.pk}/delete/")

    assert response.status_code == 409
    assert Gym.objects.count() == 1
