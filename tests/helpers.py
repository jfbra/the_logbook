from django.http import HttpResponse
from django.test import Client


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path)  # pyright: ignore[reportReturnType]


def post(client: Client, path: str, data: dict[str, str] | None = None) -> HttpResponse:
    return client.post(path, data or {})  # pyright: ignore[reportReturnType]
