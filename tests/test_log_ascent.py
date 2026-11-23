import pytest
from django.test import Client

from logbook.models import Ascent, Route

from .helpers import get, post
from .test_session_detail import log_session


SOME_GRADE = {"v": "V4", "font": "6B", "french": "6a", "ewbank": "20"}


def add(client: Client, pk: int, **fields: str):
    data = {
        "name": "Blue V4 by the cave",
        "route_type": "boulder",
        "discipline": "boulder",
        "result": "flash",
        **fields,
    }
    system = data.get("grade_system") or (
        "v" if data["route_type"] == "boulder" else "ewbank"
    )
    data.setdefault("grade", SOME_GRADE[system])
    return post(client, f"/sessions/{pk}/ascents/new/", data)


@pytest.fixture
def indoor(signed_in_client: Client) -> int:
    return log_session(signed_in_client, indoor_outdoor="indoor", location="Depot")


def test_anonymous_user_cannot_add_an_ascent():
    response = Client().post("/sessions/1/ascents/new/", {})

    assert response.status_code == 302


@pytest.mark.django_db
def test_adding_an_ascent_lists_it_on_the_session_page(
    signed_in_client: Client, indoor: int
):
    add(signed_in_client, indoor, grade="V4")

    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    assert "Blue V4 by the cave" in html
    assert "Flash" in html
    assert "No Ascents yet" not in html
    assert Route.objects.get().location == "Depot"


def test_htmx_add_returns_the_updated_section_without_a_full_page(
    signed_in_client: Client, indoor: int
):
    response = signed_in_client.post(
        f"/sessions/{indoor}/ascents/new/",
        {
            "name": "Red",
            "route_type": "boulder",
            "grade": "V2",
            "discipline": "boulder",
            "result": "send",
        },
        HTTP_HX_REQUEST="true",
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert "Red" in html
    assert "<html" not in html


@pytest.mark.django_db
def test_route_name_is_required(signed_in_client: Client, indoor: int):
    response = add(signed_in_client, indoor, name="  ")

    assert response.status_code == 422
    assert Ascent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_type", "expected"), [("boulder", "v"), ("roped", "ewbank")]
)
def test_grade_system_defaults_by_route_type(
    signed_in_client: Client, indoor: int, route_type: str, expected: str
):
    discipline = "boulder" if route_type == "boulder" else "sport"
    add(signed_in_client, indoor, route_type=route_type, discipline=discipline)

    assert Route.objects.get().grade_system == expected


@pytest.mark.django_db
def test_chosen_grade_system_is_kept(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor, grade="6B", grade_system="font")

    route = Route.objects.get()
    assert (route.grade, route.grade_system) == ("6B", "font")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_type", "discipline"),
    [("boulder", "sport"), ("boulder", "top_rope"), ("roped", "boulder")],
)
def test_discipline_must_suit_the_route_type(
    signed_in_client: Client, indoor: int, route_type: str, discipline: str
):
    response = add(
        signed_in_client,
        indoor,
        route_type=route_type,
        discipline=discipline,
        result="onsight",
    )

    assert response.status_code == 422
    assert "does not suit" in response.content.decode()
    assert Ascent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_type", "discipline", "result"),
    [
        ("boulder", "boulder", "redpoint"),
        ("boulder", "boulder", "dogged"),
        ("roped", "top_rope", "redpoint"),
        ("roped", "sport", "send"),
        ("roped", "sport", "dab"),
    ],
)
def test_result_must_be_in_the_disciplines_list(
    signed_in_client: Client,
    indoor: int,
    route_type: str,
    discipline: str,
    result: str,
):
    response = add(
        signed_in_client,
        indoor,
        route_type=route_type,
        discipline=discipline,
        result=result,
    )

    assert response.status_code == 422
    assert "is not a result for" in response.content.decode()
    assert Ascent.objects.count() == 0


@pytest.mark.django_db
def test_rests_are_kept_for_dogged(signed_in_client: Client, indoor: int):
    add(
        signed_in_client,
        indoor,
        route_type="roped",
        discipline="top_rope",
        result="dogged",
        rests="3",
    )

    assert Ascent.objects.get().rests == 3


@pytest.mark.django_db
def test_rests_are_cleared_when_not_dogged(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor, result="flash", rests="3")

    assert Ascent.objects.get().rests is None


@pytest.mark.django_db
@pytest.mark.parametrize("rests", ["0", "-1", "1.5", "two"])
def test_rests_must_be_a_positive_whole_number(
    signed_in_client: Client, indoor: int, rests: str
):
    response = add(
        signed_in_client,
        indoor,
        route_type="roped",
        discipline="sport",
        result="dogged",
        rests=rests,
    )

    assert response.status_code == 422
    assert Ascent.objects.count() == 0


@pytest.mark.django_db
def test_records_have_timestamps(signed_in_client: Client, indoor: int):
    add(signed_in_client, indoor)

    ascent = Ascent.objects.select_related("route").get()
    assert ascent.created_at and ascent.updated_at
    assert ascent.route.created_at and ascent.route.updated_at


@pytest.mark.django_db
@pytest.mark.parametrize("setting", ["outdoor", ""])
def test_adding_to_an_outdoor_or_unset_session_is_rejected(
    signed_in_client: Client, setting: str
):
    pk = log_session(signed_in_client, indoor_outdoor=setting)

    response = add(signed_in_client, pk)

    assert response.status_code == 400
    assert Ascent.objects.count() == 0
    assert Route.objects.count() == 0


@pytest.mark.django_db
def test_discipline_defaults_to_the_last_ascent_in_the_session(
    signed_in_client: Client, indoor: int
):
    add(
        signed_in_client,
        indoor,
        route_type="roped",
        discipline="top_rope",
        result="onsight",
    )
    add(
        signed_in_client,
        indoor,
        route_type="roped",
        discipline="sport",
        result="onsight",
        name="B",
    )

    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    assert '<option value="sport" selected>' in html


@pytest.mark.django_db
def test_discipline_defaults_to_the_latest_overall_for_a_fresh_session(
    signed_in_client: Client, indoor: int
):
    add(
        signed_in_client,
        indoor,
        route_type="roped",
        discipline="sport",
        result="onsight",
    )
    other = log_session(signed_in_client, indoor_outdoor="indoor")

    html = get(signed_in_client, f"/sessions/{other}/").content.decode()

    assert '<option value="sport" selected>' in html


def test_get_on_the_add_endpoint_is_not_allowed(signed_in_client: Client, indoor: int):
    assert get(signed_in_client, f"/sessions/{indoor}/ascents/new/").status_code == 405
