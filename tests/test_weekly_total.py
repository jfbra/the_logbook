import datetime

from django.test import Client
from django.utils import timezone

from .helpers import get, post, session_ids


def this_monday() -> datetime.date:
    today = timezone.localdate()
    return today - datetime.timedelta(days=today.weekday())


def log_on(client: Client, day: datetime.date, **fields: str) -> None:
    data = {"date": day.isoformat(), "activity_type": "climbing", **fields}
    assert post(client, "/sessions/new/", data).status_code == 302


def test_weekly_totals_split_on_monday_boundaries(signed_in_client: Client):
    monday = this_monday()
    day = datetime.timedelta(days=1)
    log_on(signed_in_client, monday, duration_minutes="100")  # this week
    log_on(signed_in_client, monday + 6 * day, duration_minutes="11")  # this Sunday
    log_on(signed_in_client, monday - day, duration_minutes="20")  # last Sunday
    log_on(signed_in_client, monday - 7 * day, duration_minutes="30")  # last Monday
    log_on(signed_in_client, monday - 8 * day, duration_minutes="700")  # older
    log_on(signed_in_client, monday + 7 * day, duration_minutes="9000")  # next week

    html = get(signed_in_client, "/").content.decode()

    assert "This week: 111 min" in html
    assert "Last week: 50 min" in html


def test_sessions_without_duration_count_as_zero(signed_in_client: Client):
    monday = this_monday()
    log_on(signed_in_client, monday)
    log_on(signed_in_client, monday, duration_minutes="45")

    html = get(signed_in_client, "/").content.decode()

    assert "This week: 45 min" in html
    assert "Last week: 0 min" in html


def test_totals_are_zero_with_no_sessions(signed_in_client: Client):
    html = get(signed_in_client, "/").content.decode()

    assert "This week: 0 min" in html
    assert "Last week: 0 min" in html


def test_totals_reflect_edits_and_deletes(signed_in_client: Client):
    log_on(signed_in_client, this_monday(), duration_minutes="60")
    pk = session_ids(signed_in_client)[0]

    post(
        signed_in_client,
        f"/sessions/{pk}/edit/",
        {
            "date": this_monday().isoformat(),
            "activity_type": "climbing",
            "duration_minutes": "75",
        },
    )
    assert "This week: 75 min" in get(signed_in_client, "/").content.decode()

    post(signed_in_client, f"/sessions/{pk}/delete/")
    assert "This week: 0 min" in get(signed_in_client, "/").content.decode()


def test_editing_a_sessions_date_moves_its_minutes_between_weeks(
    signed_in_client: Client,
):
    day = datetime.timedelta(days=1)
    log_on(signed_in_client, this_monday(), duration_minutes="40")
    pk = session_ids(signed_in_client)[0]

    post(
        signed_in_client,
        f"/sessions/{pk}/edit/",
        {
            "date": (this_monday() - day).isoformat(),
            "activity_type": "climbing",
            "duration_minutes": "40",
        },
    )

    html = get(signed_in_client, "/").content.decode()
    assert "This week: 0 min" in html
    assert "Last week: 40 min" in html
