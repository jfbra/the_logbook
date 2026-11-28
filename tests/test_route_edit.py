import datetime

import pytest
from django.test import Client

from logbook.models import Gym, IndoorAscent, IndoorRoute, Session

from .helpers import get, post


@pytest.fixture
def gym(db) -> Gym:
    return Gym.objects.create(name="Depot")


def make_route(gym: Gym, **kw) -> IndoorRoute:
    defaults = {"name": "Blue", "grade": "V3", "route_type": "boulder", "gym": gym}
    return IndoorRoute.objects.create(**{**defaults, **kw})


def form_data(route: IndoorRoute, **kw) -> dict[str, str]:
    data = {
        "name": route.name,
        "gym": str(route.gym_id),  # pyright: ignore[reportAttributeAccessIssue]
        "route_type": route.route_type,
        "grade_system": route.grade_system,
        "grade": route.grade,
    }
    data.update(kw)
    return data


def url(route: IndoorRoute) -> str:
    return f"/routes/{route.pk}/edit/"


def test_anonymous_user_is_redirected_to_login():
    assert Client().get("/routes/1/edit/")["Location"].startswith("/login/")
    assert Client().post("/routes/1/edit/")["Location"].startswith("/login/")


def test_unknown_route_is_not_found(signed_in_client: Client):
    assert get(signed_in_client, "/routes/999999/edit/").status_code == 404


def test_every_attribute_can_be_set_and_edited(signed_in_client: Client, gym: Gym):
    route = make_route(gym, route_type="sport", grade="20")

    response = post(
        signed_in_client,
        url(route),
        form_data(
            route,
            stars="3",
            length_m="12",
            description="Crimpy",
            setter="Sam",
            style="technical",
            hold_colour="Red",
            date_set="2026-11-01",
            rope_number="R4",
            bolts="8",
        ),
    )

    assert response.status_code == 302
    route.refresh_from_db()
    assert (route.stars, route.length_m, route.description) == (3, 12, "Crimpy")
    assert (route.setter, route.style, route.hold_colour) == ("Sam", "technical", "Red")
    assert route.date_set == datetime.date(2026, 11, 1)
    assert (route.rope_number, route.bolts, route.area) == ("R4", 8, "")


def test_boulder_area_can_be_set(signed_in_client: Client, gym: Gym):
    route = make_route(gym)

    post(signed_in_client, url(route), form_data(route, area="Cave"))

    route.refresh_from_db()
    assert route.area == "Cave"


@pytest.mark.parametrize("stars", ["-1", "4"])
def test_stars_outside_zero_to_three_are_rejected(
    signed_in_client: Client, gym: Gym, stars: str
):
    route = make_route(gym)

    response = post(signed_in_client, url(route), form_data(route, stars=stars))

    assert response.status_code == 200
    route.refresh_from_db()
    assert route.stars is None


@pytest.mark.parametrize(
    ("route_type", "extra"),
    [
        ("boulder", {"bolts": "5"}),
        ("top_rope", {"bolts": "5"}),
        ("boulder", {"rope_number": "2"}),
        ("top_rope", {"area": "Cave"}),
        ("sport", {"area": "Cave"}),
    ],
)
def test_fields_that_do_not_apply_to_the_type_are_rejected(
    signed_in_client: Client, gym: Gym, route_type: str, extra: dict[str, str]
):
    grade = "V3" if route_type == "boulder" else "20"
    route = make_route(gym, route_type=route_type, grade=grade)

    response = post(signed_in_client, url(route), form_data(route, **extra))

    assert response.status_code == 200
    route.refresh_from_db()
    assert (route.bolts, route.rope_number, route.area) == (None, "", "")


def test_route_can_be_moved_to_another_gym(signed_in_client: Client, gym: Gym):
    other = Gym.objects.create(name="Elsewhere")
    route = make_route(gym)

    response = post(signed_in_client, url(route), form_data(route, gym=str(other.pk)))

    assert response.status_code == 302
    route.refresh_from_db()
    assert route.gym == other


def test_type_can_change_while_there_are_no_ascents(signed_in_client: Client, gym: Gym):
    route = make_route(gym)

    post(
        signed_in_client,
        url(route),
        form_data(route, route_type="sport", grade_system="ewbank", grade="20"),
    )

    route.refresh_from_db()
    assert route.route_type == "sport"


def test_type_cannot_change_once_the_route_has_ascents(
    signed_in_client: Client, gym: Gym
):
    route = make_route(gym)
    session = Session.objects.create(date=datetime.date(2026, 11, 1))
    IndoorAscent.objects.create(
        session=session, route=route, discipline="boulder", result="flash"
    )

    response = post(
        signed_in_client,
        url(route),
        form_data(route, route_type="sport", grade_system="ewbank", grade="20"),
    )

    assert response.status_code == 200
    route.refresh_from_db()
    assert route.route_type == "boulder"
    assert "Route type" in response.content.decode()


def test_other_attributes_can_still_change_with_ascents(
    signed_in_client: Client, gym: Gym
):
    route = make_route(gym)
    session = Session.objects.create(date=datetime.date(2026, 11, 1))
    IndoorAscent.objects.create(
        session=session, route=route, discipline="boulder", result="flash"
    )

    response = post(signed_in_client, url(route), form_data(route, setter="Sam"))

    assert response.status_code == 302
    route.refresh_from_db()
    assert route.setter == "Sam"


def test_session_ascent_list_links_to_the_route_edit_page(
    signed_in_client: Client, gym: Gym
):
    route = make_route(gym)
    session = Session.objects.create(date=datetime.date(2026, 11, 1))
    IndoorAscent.objects.create(
        session=session, route=route, discipline="boulder", result="flash"
    )

    html = get(signed_in_client, f"/sessions/{session.pk}/").content.decode()

    assert url(route) in html


@pytest.mark.parametrize("field", ["length_m", "bolts"])
def test_length_and_bolts_must_be_positive(
    signed_in_client: Client, gym: Gym, field: str
):
    route = make_route(gym, route_type="sport", grade="20")

    response = post(signed_in_client, url(route), form_data(route, **{field: "0"}))

    assert response.status_code == 200
    route.refresh_from_db()
    assert getattr(route, field) is None
