import re

import pytest
from django.test import Client

from logbook.grades import GRADES_BY_SYSTEM
from logbook.models import Ascent, Route

from .helpers import get
from .test_log_ascent import add
from .test_session_detail import log_session


@pytest.fixture
def indoor(signed_in_client: Client) -> int:
    return log_session(signed_in_client, indoor_outdoor="indoor", location="Depot")


def options(html: str) -> list[str]:
    """Values of the <option>s in a fragment or in the grade <select> of a page."""
    select = re.search(r'<select[^>]*name="grade".*?</select>', html, re.S)
    if select:
        html = select.group(0)
    return re.findall(r'<option value="([^"]*)"', html)


def test_the_grade_lists_have_the_specified_ranges_in_order():
    v, font, french, ewbank = (
        GRADES_BY_SYSTEM[s] for s in ("v", "font", "french", "ewbank")
    )

    assert v[:3] == ["VB", "V0", "V1"] and v[-1] == "V17" and len(v) == 19
    assert font[:8] == ["3", "4", "4+", "5", "5+", "6A", "6A+", "6B"]
    assert font[font.index("6C+") + 1 :][:2] == ["7A", "7A+"]
    assert font[-1] == "9A" and font[-2] == "8C+"
    assert french[:11] == [
        "1",
        "2",
        "3",
        "3+",
        "4a",
        "4b",
        "4c",
        "5a",
        "5b",
        "5c",
        "6a",
    ]
    assert french[-5:] == ["9a", "9a+", "9b", "9b+", "9c"]
    assert french[french.index("6c+") + 1] == "7a"
    assert ewbank == [str(n) for n in range(1, 40)]
    for grades in GRADES_BY_SYSTEM.values():
        assert len(grades) == len(set(grades))


@pytest.mark.django_db
def test_creating_a_route_without_a_grade_is_rejected(
    signed_in_client: Client, indoor: int
):
    response = add(signed_in_client, indoor, grade="")

    assert response.status_code == 422
    assert "A grade is required." in response.content.decode()
    assert not Route.objects.exists()
    assert not Ascent.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_type", "grade_system", "grade"),
    [
        ("boulder", "", "6B"),  # a Font grade for a V boulder
        ("boulder", "", "V18"),
        ("roped", "", "V4"),  # a V grade for an Ewbank route
        ("roped", "", "40"),
        ("roped", "french", "20"),
        ("boulder", "font", "V4"),
        ("boulder", "font", "6b"),  # case matters: Font is upper-case
        ("boulder", "", "not a grade"),
    ],
)
def test_a_grade_outside_the_systems_list_is_rejected(
    signed_in_client: Client,
    indoor: int,
    route_type: str,
    grade_system: str,
    grade: str,
):
    discipline = "boulder" if route_type == "boulder" else "sport"
    response = add(
        signed_in_client,
        indoor,
        route_type=route_type,
        discipline=discipline,
        grade_system=grade_system,
        grade=grade,
    )

    assert response.status_code == 422
    assert not Route.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("grade_system", "grade"),
    [("v", "VB"), ("font", "9A"), ("french", "3+"), ("ewbank", "39"), ("", "V17")],
)
def test_a_grade_in_the_systems_list_is_accepted(
    signed_in_client: Client, indoor: int, grade_system: str, grade: str
):
    response = add(signed_in_client, indoor, grade_system=grade_system, grade=grade)

    assert response.status_code == 302
    assert Route.objects.get().grade == grade


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_type", "expected"), [("boulder", "v"), ("roped", "ewbank")]
)
def test_the_default_grade_system_still_follows_the_type(
    signed_in_client: Client, indoor: int, route_type: str, expected: str
):
    discipline = "boulder" if route_type == "boulder" else "sport"
    add(signed_in_client, indoor, route_type=route_type, discipline=discipline)

    assert Route.objects.get().grade_system == expected


@pytest.mark.django_db
@pytest.mark.parametrize("system", ["v", "font", "french", "ewbank"])
def test_the_grade_choices_follow_the_chosen_system(
    signed_in_client: Client, system: str
):
    html = get(signed_in_client, f"/grades/options/?grade_system={system}").content
    assert options(html.decode()) == ["", *GRADES_BY_SYSTEM[system]]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_type", "system"), [("boulder", "v"), ("roped", "ewbank")]
)
def test_the_grade_choices_default_from_the_type(
    signed_in_client: Client, route_type: str, system: str
):
    html = get(signed_in_client, f"/grades/options/?route_type={route_type}").content

    assert options(html.decode()) == ["", *GRADES_BY_SYSTEM[system]]


@pytest.mark.django_db
def test_an_explicit_system_beats_the_types_default(signed_in_client: Client):
    html = get(
        signed_in_client, "/grades/options/?route_type=boulder&grade_system=font"
    ).content

    assert options(html.decode()) == ["", *GRADES_BY_SYSTEM["font"]]


@pytest.mark.django_db
def test_an_unknown_system_offers_no_grades(signed_in_client: Client):
    html = get(signed_in_client, "/grades/options/?grade_system=bogus").content

    assert options(html.decode()) == [""]


def test_anonymous_user_cannot_fetch_grade_options():
    assert Client().get("/grades/options/").status_code == 302


@pytest.mark.django_db
def test_the_session_page_offers_a_grade_choice_that_refetches_on_change(
    signed_in_client: Client, indoor: int
):
    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    assert options(html)[:2] == ["", "VB"]
    assert 'hx-get="/grades/options/"' in html


@pytest.mark.django_db
def test_a_rejected_form_offers_the_chosen_systems_grades(
    signed_in_client: Client, indoor: int
):
    html = add(
        signed_in_client, indoor, grade_system="font", grade="V4"
    ).content.decode()

    assert options(html) == ["", *GRADES_BY_SYSTEM["font"]]


@pytest.mark.django_db
def test_logging_an_ascent_of_an_existing_route_needs_no_grade(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, name="Blue Cave")
    route = Route.objects.get()

    response = signed_in_client.post(
        f"/sessions/{indoor}/ascents/new/",
        {"route": str(route.pk), "discipline": "boulder", "result": "repeat"},
    )

    assert response.status_code == 302
    assert Ascent.objects.count() == 2
