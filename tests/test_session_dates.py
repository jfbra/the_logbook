import datetime

import pytest
from django.test import Client

from logbook.models import IndoorAscent as Ascent, IndoorRoute as Route, Session

from .helpers import get, post, session_ids
from .test_log_ascent import add
from .test_session_detail import log_session

START = datetime.date(2026, 11, 20)


def edit_session(client: Client, pk: int, date: str, end_date: str = ""):
    return post(client, f"/sessions/{pk}/edit/", {"date": date, "end_date": end_date})


@pytest.fixture
def trip(signed_in_client: Client) -> int:
    """A Session running 20-22 November."""
    return log_session(signed_in_client, end_date="2026-11-22")


@pytest.mark.parametrize("end_date", ["", "2026-11-20", "2026-11-23"])
def test_a_session_can_be_created_with_or_without_an_end_date(
    signed_in_client: Client, end_date: str
):
    log_session(signed_in_client, end_date=end_date)

    saved = Session.objects.get().end_date
    assert saved == (datetime.date.fromisoformat(end_date) if end_date else None)


def test_an_end_date_before_the_start_is_rejected(signed_in_client: Client):
    response = post(
        signed_in_client,
        "/sessions/new/",
        {"date": "2026-11-20", "end_date": "2026-11-19"},
    )

    assert response.status_code == 200
    assert "cannot be before the start date" in response.content.decode()
    assert Session.objects.count() == 0


@pytest.mark.parametrize("name", ["activity_type", "indoor_outdoor", "location"])
def test_the_session_form_has_no_activity_type_setting_or_location(
    signed_in_client: Client, name: str
):
    html = get(signed_in_client, "/sessions/new/").content.decode()

    assert f'name="{name}"' not in html
    assert 'name="end_date"' in html


def test_the_list_and_page_show_the_date_range(signed_in_client: Client, trip: int):
    for path in ["/", f"/sessions/{trip}/", f"/sessions/{trip}/delete/"]:
        html = get(signed_in_client, path).content.decode()

        assert "2026-11-20 to 2026-11-22" in html, path


@pytest.mark.parametrize("given", [None, ""])
def test_an_ascents_date_defaults_to_the_session_start(
    signed_in_client: Client, trip: int, given: str | None
):
    fields = {} if given is None else {"date": given}

    assert add(signed_in_client, trip, **fields).status_code == 302

    assert Ascent.objects.get().date == START


def test_the_add_form_offers_the_session_start_as_the_date(
    signed_in_client: Client, trip: int
):
    html = get(signed_in_client, f"/sessions/{trip}/").content.decode()

    assert 'name="date" value="2026-11-20"' in html


@pytest.mark.parametrize("day", ["2026-11-20", "2026-11-21", "2026-11-22"])
def test_an_ascent_can_be_dated_within_the_range(
    signed_in_client: Client, trip: int, day: str
):
    assert add(signed_in_client, trip, date=day).status_code == 302

    assert Ascent.objects.get().date.isoformat() == day


@pytest.mark.parametrize("day", ["2026-11-19", "2026-11-23"])
def test_an_ascent_dated_outside_the_range_is_rejected(
    signed_in_client: Client, trip: int, day: str
):
    response = add(signed_in_client, trip, date=day)

    assert response.status_code == 422
    assert "within the Session" in response.content.decode()
    assert Ascent.objects.count() == 0
    assert Route.objects.count() == 0


def test_without_an_end_date_the_ascent_must_be_on_the_start_date(
    signed_in_client: Client,
):
    pk = log_session(signed_in_client)

    assert add(signed_in_client, pk, date="2026-11-21").status_code == 422
    assert Ascent.objects.count() == 0


def edit_ascent(client: Client, ascent: Ascent, date: str):
    return post(
        client,
        f"/ascents/{ascent.pk}/edit/",
        {"date": date, "discipline": "boulder", "result": "flash"},
    )


def test_the_ascent_edit_page_changes_the_date(signed_in_client: Client, trip: int):
    add(signed_in_client, trip)
    ascent = Ascent.objects.get()
    page = get(signed_in_client, f"/ascents/{ascent.pk}/edit/").content.decode()
    assert 'value="2026-11-20"' in page

    assert edit_ascent(signed_in_client, ascent, "2026-11-22").status_code == 302

    ascent.refresh_from_db()
    assert ascent.date == datetime.date(2026, 11, 22)


@pytest.mark.parametrize("bad", ["", "2026-11-23"])
def test_the_ascent_edit_page_rejects_a_bad_date(
    signed_in_client: Client, trip: int, bad: str
):
    add(signed_in_client, trip, date="2026-11-21")
    ascent = Ascent.objects.get()

    response = edit_ascent(signed_in_client, ascent, bad)

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()
    ascent.refresh_from_db()
    assert ascent.date == datetime.date(2026, 11, 21)


@pytest.mark.parametrize(
    ("date", "end_date"),
    [
        ("2026-11-22", "2026-11-22"),  # starts after the Ascent
        ("2026-11-20", "2026-11-20"),  # ends before it
        ("2026-11-20", ""),  # shrinks to the start day alone
    ],
)
def test_a_date_change_that_would_orphan_an_ascent_is_rejected(
    signed_in_client: Client, trip: int, date: str, end_date: str
):
    add(signed_in_client, trip, date="2026-11-21")

    response = edit_session(signed_in_client, trip, date, end_date)

    assert response.status_code == 200
    assert "1 Ascent would fall outside" in response.content.decode()
    session = Session.objects.get()
    assert (session.date, session.end_date) == (START, datetime.date(2026, 11, 22))


def test_a_date_change_that_keeps_every_ascent_is_accepted(
    signed_in_client: Client, trip: int
):
    add(signed_in_client, trip, date="2026-11-21")

    response = edit_session(signed_in_client, trip, "2026-11-21")

    assert response.status_code == 302


def test_the_list_and_page_show_each_gym_once(signed_in_client: Client):
    pk = log_session(signed_in_client)
    add(signed_in_client, pk, gym="Zenith")
    add(signed_in_client, pk, gym="apex", name="Two")
    add(signed_in_client, pk, gym="Zenith", name="Three")

    listing = get(signed_in_client, "/").content.decode()
    page = get(signed_in_client, f"/sessions/{pk}/").content.decode()

    assert '<td data-label="Gyms">apex, Zenith</td>' in listing
    assert "Gyms: apex, Zenith" in page


def test_a_session_only_shows_its_own_gyms(signed_in_client: Client):
    first = log_session(signed_in_client)
    add(signed_in_client, first, gym="Zenith")
    log_session(signed_in_client, date="2026-11-10")
    empty = session_ids(signed_in_client)[-1]

    page = get(signed_in_client, f"/sessions/{empty}/").content.decode()

    assert "Gyms:" not in page
    assert '<td data-label="Gyms"></td>' in get(signed_in_client, "/").content.decode()


def test_adding_over_htmx_returns_the_updated_gyms(signed_in_client: Client):
    pk = log_session(signed_in_client)

    response = signed_in_client.post(
        f"/sessions/{pk}/ascents/new/",
        {
            "gym": "Zenith",
            "name": "Red",
            "route_type": "boulder",
            "grade": "V2",
            "discipline": "boulder",
            "result": "tick",
        },
        HTTP_HX_REQUEST="true",
    )

    assert "Gyms: Zenith" in response.content.decode()


def test_ascents_are_listed_in_date_order(signed_in_client: Client, trip: int):
    add(signed_in_client, trip, name="Later", date="2026-11-22")
    add(signed_in_client, trip, name="Earlier", date="2026-11-20")

    html = get(signed_in_client, f"/sessions/{trip}/").content.decode()

    assert html.index("Earlier</a>") < html.index("Later</a>")


def test_a_search_match_shows_the_result_of_the_latest_dated_ascent(
    signed_in_client: Client, trip: int
):
    add(signed_in_client, trip, name="Cave", date="2026-11-22", result="dab")
    route = Route.objects.get()
    add(
        signed_in_client,
        trip,
        route=str(route.pk),
        date="2026-11-20",
        result="working",
    )

    html = get(
        signed_in_client, f"/sessions/{trip}/routes/search/?gym=Depot&name=Cave"
    ).content.decode()

    assert "last: Dab" in html


def test_the_orphan_error_explains_how_to_move_ascents(signed_in_client: Client):
    pk = log_session(signed_in_client)
    add(signed_in_client, pk)

    response = edit_session(signed_in_client, pk, "2026-11-21")

    assert "first widen the dates" in response.content.decode()


@pytest.mark.parametrize(
    ("date", "end_date"),
    [("", "2026-11-19"), ("2026-11-23", "not a date")],
)
def test_a_bad_date_field_raises_no_second_error_from_the_old_value(
    signed_in_client: Client, trip: int, date: str, end_date: str
):
    add(signed_in_client, trip, date="2026-11-21")

    html = edit_session(signed_in_client, trip, date, end_date).content.decode()

    assert "errorlist" in html
    assert "cannot be before the start date" not in html
    assert "would fall outside" not in html


def test_choosing_a_route_keeps_the_typed_date(signed_in_client: Client, trip: int):
    add(signed_in_client, trip)
    route = Route.objects.get()
    form = f"/sessions/{trip}/ascents/form/"

    chosen = get(signed_in_client, f"{form}?route={route.pk}&date=2026-11-22")
    cleared = get(signed_in_client, f"{form}?date=2026-11-22")

    for response in [chosen, cleared]:
        html = response.content.decode()
        assert 'name="date" value="2026-11-22"' in html
    # Only a chosen Route has the "Change route" link.
    assert 'hx-include="#id_date"' in chosen.content.decode()


def test_the_route_matches_send_the_typed_date(signed_in_client: Client, trip: int):
    add(signed_in_client, trip, name="Cave")

    html = get(
        signed_in_client, f"/sessions/{trip}/routes/search/?gym=Depot&name=Cave"
    ).content.decode()

    assert 'hx-include="#id_date"' in html


@pytest.mark.parametrize("bad", ["", "nonsense", "2026-02-30"])
def test_an_unusable_typed_date_falls_back_to_the_start(
    signed_in_client: Client, trip: int, bad: str
):
    response = get(signed_in_client, f"/sessions/{trip}/ascents/form/?date={bad}")

    assert 'name="date" value="2026-11-20"' in response.content.decode()


def test_the_ascent_delete_confirmation_shows_the_date(
    signed_in_client: Client, trip: int
):
    add(signed_in_client, trip, date="2026-11-21")
    ascent = Ascent.objects.get()

    html = get(signed_in_client, f"/ascents/{ascent.pk}/delete/").content.decode()

    assert "2026-11-21" in html
