import re

import pytest
from django.test import Client

from .helpers import get
from .test_log_ascent import ALLOWED, add
from .test_session_detail import log_session


@pytest.fixture
def indoor(signed_in_client: Client) -> int:
    return log_session(signed_in_client, indoor_outdoor="indoor", location="Depot")


def option_values(html: str, select_name: str | None = None) -> list[str]:
    if select_name:
        html = re.search(
            rf'<select[^>]*name="{select_name}".*?</select>', html, re.S
        ).group(0)  # pyright: ignore[reportOptionalMemberAccess]
    return re.findall(r'<option value="([^"]*)"', html)


RESULTS_BY_DISCIPLINE = {
    "sport": ALLOWED[("sport", "sport")],
    "top_rope": ALLOWED[("top_rope", "top_rope")],
    "boulder": ALLOWED[("boulder", "boulder")],
}


@pytest.mark.django_db
@pytest.mark.parametrize("discipline", RESULTS_BY_DISCIPLINE)
def test_result_options_depend_only_on_the_discipline(
    signed_in_client: Client, discipline: str
):
    html = get(signed_in_client, f"/results/options/?discipline={discipline}").content

    assert option_values(html.decode()) == RESULTS_BY_DISCIPLINE[discipline]


@pytest.mark.django_db
def test_unknown_discipline_offers_no_results(signed_in_client: Client):
    html = get(signed_in_client, "/results/options/?discipline=nope").content

    assert option_values(html.decode()) == []


@pytest.mark.django_db
def test_the_add_form_offers_results_for_its_first_discipline(
    signed_in_client: Client, indoor: int
):
    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    first = option_values(html, "discipline")[0]
    assert option_values(html, "result") == RESULTS_BY_DISCIPLINE[first]


@pytest.mark.django_db
def test_discipline_select_asks_the_server_for_matching_results(
    signed_in_client: Client, indoor: int
):
    html = get(signed_in_client, f"/sessions/{indoor}/").content.decode()

    tag = re.search(r'<select[^>]*name="discipline"[^>]*>', html).group(0)  # pyright: ignore[reportOptionalMemberAccess]
    assert 'hx-get="/results/options/"' in tag
    assert 'hx-target="#id_result"' in tag


@pytest.mark.django_db
def test_a_rejected_form_keeps_results_narrowed_to_the_posted_discipline(
    signed_in_client: Client, indoor: int
):
    response = add(signed_in_client, indoor, discipline="boulder", result="redpoint")

    assert response.status_code == 422
    html = response.content.decode()
    assert option_values(html, "result") == RESULTS_BY_DISCIPLINE["boulder"]


@pytest.mark.django_db
def test_edit_page_offers_results_for_the_ascents_discipline(
    signed_in_client: Client, indoor: int
):
    from logbook.models import IndoorAscent

    add(
        signed_in_client,
        indoor,
        route_type="sport",
        discipline="top_rope",
        result="dogged",
        rests="2",
    )
    ascent = IndoorAscent.objects.get()

    html = get(signed_in_client, f"/ascents/{ascent.pk}/edit/").content.decode()

    assert option_values(html, "result") == RESULTS_BY_DISCIPLINE["top_rope"]
    tag = re.search(r'<select[^>]*name="discipline"[^>]*>', html).group(0)  # pyright: ignore[reportOptionalMemberAccess]
    assert 'hx-get="/results/options/"' in tag


@pytest.mark.django_db
def test_edit_page_keeps_a_stored_result_that_no_longer_fits(
    signed_in_client: Client, indoor: int
):
    from logbook.models import IndoorAscent

    add(signed_in_client, indoor, discipline="boulder", result="flash")
    ascent = IndoorAscent.objects.get()
    IndoorAscent.objects.filter(pk=ascent.pk).update(result="redpoint")

    html = get(signed_in_client, f"/ascents/{ascent.pk}/edit/").content.decode()

    assert "redpoint" in option_values(html, "result")
    assert re.search(r'<option value="redpoint" selected', html)


@pytest.mark.django_db
def test_result_options_marks_the_current_result_when_still_valid(
    signed_in_client: Client,
):
    html = get(
        signed_in_client, "/results/options/?discipline=sport&result=dogged"
    ).content.decode()

    assert '<option value="dogged" selected>' in html
