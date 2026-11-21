from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

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
    return render(
        request, "logbook/session_form.html", {"form": form, "title": "Log a Session"}
    )


def session_edit(request: HttpRequest, pk: int) -> HttpResponse:
    session = get_object_or_404(Session, pk=pk)
    form = SessionForm(request.POST or None, instance=session)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("session_list")
    return render(
        request,
        "logbook/session_form.html",
        {"form": form, "title": "Edit Session", "session": session},
    )


def session_delete(request: HttpRequest, pk: int) -> HttpResponse:
    session = get_object_or_404(Session, pk=pk)
    if request.method == "POST":
        session.delete()
        return redirect("session_list")
    return render(request, "logbook/session_confirm_delete.html", {"session": session})
