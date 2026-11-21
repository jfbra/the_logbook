from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def session_list(request: HttpRequest) -> HttpResponse:
    return render(request, "logbook/session_list.html", {"sessions": []})
