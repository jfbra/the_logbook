import json

from django.contrib.staticfiles import finders
from django.test import Client

from .helpers import get

def test_manifest_is_served_without_login_and_is_valid(db):
    response = get(Client(), "/manifest.webmanifest")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/manifest+json")
    manifest = json.loads(response.content)
    assert manifest["name"] == "The Logbook"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_manifest_icons_exist_as_static_files(db):
    manifest = json.loads(get(Client(), "/manifest.webmanifest").content)

    for icon in manifest["icons"]:
        relative = icon["src"].removeprefix("/static/")
        assert finders.find(relative), f"missing icon {icon['src']}"


def test_every_page_is_phone_ready_and_links_the_manifest(signed_in_client: Client):
    anonymous_login = get(Client(), "/login/").content.decode()
    pages = [anonymous_login]
    for path in ["/", "/sessions/new/"]:
        pages.append(get(signed_in_client, path).content.decode())

    for html in pages:
        assert 'name="viewport"' in html
        assert "width=device-width" in html
        assert "/manifest.webmanifest" in html


def test_no_service_worker_is_introduced(signed_in_client: Client):
    html = get(signed_in_client, "/").content.decode()

    assert "serviceWorker" not in html
    assert get(signed_in_client, "/sw.js").status_code == 404
