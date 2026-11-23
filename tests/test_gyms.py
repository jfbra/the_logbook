import pytest
from django.test import Client

from logbook.forms import GymForm
from logbook.models import Gym

from .helpers import get, post


def test_anonymous_user_cannot_reach_the_gym_pages():
    client = Client()

    assert client.get("/gyms/").status_code == 302
    assert client.post("/gyms/new/", {"name": "Depot"}).status_code == 302


@pytest.mark.django_db
def test_a_gym_can_be_created_with_only_a_name(signed_in_client: Client):
    response = post(signed_in_client, "/gyms/new/", {"name": "Depot"})

    assert response.status_code == 302
    gym = Gym.objects.get()
    assert (gym.name, gym.city, gym.country, gym.website) == ("Depot", "", "", "")
    assert "Depot" in get(signed_in_client, "/gyms/").content.decode()


@pytest.mark.django_db
def test_a_gym_can_be_created_with_every_field(signed_in_client: Client):
    post(
        signed_in_client,
        "/gyms/new/",
        {
            "name": "Depot",
            "city": "Wellington",
            "country": "New Zealand",
            "website": "https://depot.example.com",
        },
    )

    html = get(signed_in_client, "/gyms/").content.decode()

    assert "Wellington" in html
    assert "New Zealand" in html
    assert "https://depot.example.com" in html


@pytest.mark.django_db
def test_a_gym_needs_a_name(signed_in_client: Client):
    response = post(signed_in_client, "/gyms/new/", {"name": "   "})

    assert response.status_code == 200
    assert not Gym.objects.exists()


@pytest.mark.django_db
def test_duplicate_names_are_rejected_ignoring_case(signed_in_client: Client):
    Gym.objects.create(name="Depot")

    response = post(signed_in_client, "/gyms/new/", {"name": " dEPOT "})

    assert response.status_code == 200
    assert "A Gym called Depot already exists." in response.content.decode()
    assert Gym.objects.count() == 1


@pytest.mark.django_db
def test_the_list_is_ordered_by_name_ignoring_case(signed_in_client: Client):
    for name in ["boulder barn", "Alpha", "Depot"]:
        Gym.objects.create(name=name)

    html = get(signed_in_client, "/gyms/").content.decode()

    assert html.index("Alpha") < html.index("boulder barn") < html.index("Depot")


@pytest.mark.django_db
def test_a_gym_can_be_renamed_and_its_details_edited(signed_in_client: Client):
    gym = Gym.objects.create(name="Depot")

    post(
        signed_in_client,
        f"/gyms/{gym.pk}/edit/",
        {"name": "The Depot", "city": "Wellington"},
    )

    gym.refresh_from_db()
    assert (gym.name, gym.city) == ("The Depot", "Wellington")


@pytest.mark.django_db
def test_editing_a_gym_keeps_its_own_name_allowed(signed_in_client: Client):
    gym = Gym.objects.create(name="Depot")

    response = post(
        signed_in_client, f"/gyms/{gym.pk}/edit/", {"name": "DEPOT", "city": "Nelson"}
    )

    assert response.status_code == 302
    gym.refresh_from_db()
    assert (gym.name, gym.city) == ("DEPOT", "Nelson")


@pytest.mark.django_db
def test_renaming_to_another_gyms_name_is_rejected(signed_in_client: Client):
    Gym.objects.create(name="Depot")
    other = Gym.objects.create(name="Barn")

    response = post(signed_in_client, f"/gyms/{other.pk}/edit/", {"name": "depot"})

    assert response.status_code == 200
    other.refresh_from_db()
    assert other.name == "Barn"


@pytest.mark.django_db
def test_a_gym_can_be_deleted(signed_in_client: Client):
    gym = Gym.objects.create(name="Depot")

    page = get(signed_in_client, f"/gyms/{gym.pk}/delete/")
    response = post(signed_in_client, f"/gyms/{gym.pk}/delete/")

    assert page.status_code == 200
    assert response.status_code == 302
    assert not Gym.objects.exists()


@pytest.mark.django_db
def test_a_duplicate_that_slips_past_validation_is_rejected_not_a_server_error(
    signed_in_client: Client, monkeypatch: pytest.MonkeyPatch
):
    # The database constraint backs up the form's own check (Django validates it too).
    Gym.objects.create(name="Depot")
    monkeypatch.setattr(GymForm, "clean_name", lambda self: self.cleaned_data["name"])

    response = post(signed_in_client, "/gyms/new/", {"name": "depot"})

    assert response.status_code == 200
    assert Gym.objects.count() == 1
