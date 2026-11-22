from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import NewRouteAscentForm, SessionForm
from .models import Session, Setting
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


def _ascent_context(session: Session, form) -> dict:
    if form is None and session.indoor_outdoor == Setting.INDOOR:
        form = NewRouteAscentForm(session=session)
    return {
        "session": session,
        "form": form,
        "ascents": session.ascents.select_related("route"),  # pyright: ignore[reportAttributeAccessIssue]
    }


def session_detail(request: HttpRequest, pk: int) -> HttpResponse:
    session = get_object_or_404(Session, pk=pk)
    return render(
        request, "logbook/session_detail.html", _ascent_context(session, None)
    )


@require_POST
def ascent_create(request: HttpRequest, pk: int) -> HttpResponse:
    session = get_object_or_404(Session, pk=pk)
    if session.indoor_outdoor != Setting.INDOOR:
        return HttpResponseBadRequest("Ascents can only be added to indoor Sessions.")
    form = NewRouteAscentForm(request.POST, session=session)
    if form.is_valid():
        form.save()
        form = None
    context = _ascent_context(session, form)
    if request.headers.get("HX-Request"):
        return render(request, "logbook/_ascents.html", context)
    if form is None:
        return redirect("session_detail", pk=pk)
    return render(request, "logbook/session_detail.html", context, status=422)


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
