from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AscentEditForm, AscentForm, SessionForm, grade_choices, routes_at
from .models import Ascent, Route, Session, Setting
from .weekly import weekly_totals


def session_list(request: HttpRequest) -> HttpResponse:
    totals = weekly_totals()
    context = {
        "sessions": Session.objects.annotate(ascent_count=Count("ascents")).order_by(
            "-date", "-id"
        ),
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
        form = AscentForm(session=session)
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
    form = AscentForm(request.POST, session=session)
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
    context = {"session": session, "ascent_count": session.ascents.count()}  # pyright: ignore[reportAttributeAccessIssue]
    return render(request, "logbook/session_confirm_delete.html", context)


def _indoor_session_or_404(pk: int) -> Session:
    session = get_object_or_404(Session, pk=pk)
    if session.indoor_outdoor != Setting.INDOOR:
        raise Http404("Ascents can only be added to indoor Sessions.")
    return session


def route_search(request: HttpRequest, pk: int) -> HttpResponse:
    """Candidate Routes at the Session's location, with grade and last result."""
    session = _indoor_session_or_404(pk)
    query = request.GET.get("name", "").strip()
    candidates: list[tuple[Route, Ascent | None]] = []
    if query:
        for route in routes_at(session, query)[:10]:
            last = route.ascents.order_by("-created_at", "-id").first()  # pyright: ignore[reportAttributeAccessIssue]
            candidates.append((route, last))
    context = {"session": session, "candidates": candidates, "query": query}
    return render(request, "logbook/_route_matches.html", context)


def ascent_form(request: HttpRequest, pk: int) -> HttpResponse:
    """The quick-add section with an existing Route chosen (or cleared)."""
    session = _indoor_session_or_404(pk)
    raw = request.GET.get("route", "")
    route = (
        routes_at(session).filter(pk=int(raw)).first()
        if raw.isascii() and raw.isdigit()
        else None
    )
    form = AscentForm(session=session, route=route)
    return render(request, "logbook/_ascents.html", _ascent_context(session, form))


def ascent_edit(request: HttpRequest, pk: int) -> HttpResponse:
    ascent = get_object_or_404(Ascent.objects.select_related("session", "route"), pk=pk)
    if ascent.session.indoor_outdoor != Setting.INDOOR:
        raise Http404("Ascents can only be edited on indoor Sessions.")
    form = AscentEditForm(
        request.POST if request.method == "POST" else None, instance=ascent
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("session_detail", pk=ascent.session_id)  # pyright: ignore[reportAttributeAccessIssue]
    return render(request, "logbook/ascent_form.html", {"form": form, "ascent": ascent})


def ascent_delete(request: HttpRequest, pk: int) -> HttpResponse:
    ascent = get_object_or_404(Ascent.objects.select_related("session", "route"), pk=pk)
    if request.method == "POST":
        ascent.delete()
        return redirect("session_detail", pk=ascent.session_id)  # pyright: ignore[reportAttributeAccessIssue]
    return render(request, "logbook/ascent_confirm_delete.html", {"ascent": ascent})


def grade_options(request: HttpRequest) -> HttpResponse:
    """The grade <option>s for the chosen Route type and grade system."""
    choices = grade_choices(
        request.GET.get("route_type", ""), request.GET.get("grade_system", "")
    )
    return render(request, "logbook/_grade_options.html", {"choices": choices})
