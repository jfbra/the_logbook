from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .forms import SessionForm
from .models import Session


def session_list(request: HttpRequest) -> HttpResponse:
    return render(
        request, "logbook/session_list.html", {"sessions": Session.objects.all()}
    )


def session_create(request: HttpRequest) -> HttpResponse:
    form = SessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("session_list")
    return render(request, "logbook/session_form.html", {"form": form})
