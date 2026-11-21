from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SessionForm
from .models import Session
from .weekly import weekly_totals


def session_list(request: HttpRequest) -> HttpResponse:
    totals = weekly_totals()
    context = {
        "sessions": Session.objects.all(),
        "this_week_minutes": totals.this_week,
        "last_week_minutes": totals.last_week,
    }
    return render(request, "logbook/session_list.html", context)


def _session_form_view(
    request: HttpRequest, title: str, session: Session | None = None
) -> HttpResponse:
    form = SessionForm(request.POST or None, instance=session)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("session_list")
    context = {"form": form, "title": title, "session": session}
    return render(request, "logbook/session_form.html", context)


def session_create(request: HttpRequest) -> HttpResponse:
    return _session_form_view(request, "Log a Session")


def session_edit(request: HttpRequest, pk: int) -> HttpResponse:
    return _session_form_view(
        request, "Edit Session", get_object_or_404(Session, pk=pk)
    )


def session_delete(request: HttpRequest, pk: int) -> HttpResponse:
    session = get_object_or_404(Session, pk=pk)
    if request.method == "POST":
        session.delete()
        return redirect("session_list")
    return render(request, "logbook/session_confirm_delete.html", {"session": session})
