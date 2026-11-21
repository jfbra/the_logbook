import re

from django.http import HttpResponse
from django.test import Client


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path)  # pyright: ignore[reportReturnType]


def post(client: Client, path: str, data: dict[str, str] | None = None) -> HttpResponse:
    return client.post(path, data or {})  # pyright: ignore[reportReturnType]


def session_ids(client: Client) -> list[int]:
    """Ids of listed Sessions, read from the edit links on the list page."""
    html = get(client, "/").content.decode()
    return [int(i) for i in re.findall(r"/sessions/(\d+)/edit/", html)]
