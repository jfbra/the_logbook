import json
import struct

from django.contrib.staticfiles import finders
from django.test import Client

from .helpers import get, post, session_ids


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


def test_manifest_icons_exist_with_the_declared_dimensions(db):
    # Static files aren't served by the test client (DEBUG is off), so locate
    # them through the finders and read the PNG header for the real size.
    manifest = json.loads(get(Client(), "/manifest.webmanifest").content)

    for icon in manifest["icons"]:
        path = finders.find(icon["src"].removeprefix("/static/"))
        assert path, f"missing icon {icon['src']}"
        with open(path, "rb") as f:
            header = f.read(24)
        width, height = struct.unpack(">II", header[16:24])
        assert f"{width}x{height}" == icon["sizes"]


def test_every_page_is_phone_ready_and_links_the_manifest(signed_in_client: Client):
    post(
        signed_in_client,
        "/sessions/new/",
        {"date": "2026-11-20", "activity_type": "climbing"},
    )
    pk = session_ids(signed_in_client)[0]
    pages = [get(Client(), "/login/")]
    for path in [
        "/",
        "/sessions/new/",
        f"/sessions/{pk}/edit/",
        f"/sessions/{pk}/delete/",
    ]:
        pages.append(get(signed_in_client, path))

    for response in pages:
        html = response.content.decode()
        assert response.status_code == 200
        assert 'name="viewport"' in html
        assert "width=device-width" in html
        assert "/manifest.webmanifest" in html


def test_no_service_worker_is_introduced(signed_in_client: Client):
    html = get(signed_in_client, "/").content.decode()

    assert "serviceWorker" not in html
    assert get(signed_in_client, "/sw.js").status_code == 404
