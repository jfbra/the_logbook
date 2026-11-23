from django.db import IntegrityError
from django.db.models import Count, ProtectedError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AscentEditForm,
    AscentForm,
    GymForm,
    SessionForm,
    grade_choices,
    routes_at,
)
from .models import Gym, IndoorAscent, IndoorRoute, Session, Setting
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
    """Candidate Routes at the named Gym, with grade, colour, set date, last result."""
    session = _indoor_session_or_404(pk)
    gym = request.GET.get("gym", "").strip()
    query = request.GET.get("name", "").strip()
    candidates: list[tuple[IndoorRoute, IndoorAscent | None]] = []
    if gym and query:
        for route in routes_at(gym, query)[:10]:
            last = route.ascents.order_by("-created_at", "-id").first()  # pyright: ignore[reportAttributeAccessIssue]
            candidates.append((route, last))
    context = {"session": session, "candidates": candidates, "query": query}
    return render(request, "logbook/_route_matches.html", context)


def ascent_form(request: HttpRequest, pk: int) -> HttpResponse:
    """The quick-add section with an existing Route chosen (or cleared)."""
    session = _indoor_session_or_404(pk)
    raw = request.GET.get("route", "")
    route = (
        IndoorRoute.objects.select_related("gym").filter(pk=int(raw)).first()
        if raw.isascii() and raw.isdigit()
        else None
    )
    form = AscentForm(session=session, route=route)
    return render(request, "logbook/_ascents.html", _ascent_context(session, form))


def ascent_edit(request: HttpRequest, pk: int) -> HttpResponse:
    ascent = get_object_or_404(
        IndoorAscent.objects.select_related("session", "route"), pk=pk
    )
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
    ascent = get_object_or_404(
        IndoorAscent.objects.select_related("session", "route"), pk=pk
    )
    if request.method == "POST":
        ascent.delete()
        return redirect("session_detail", pk=ascent.session_id)  # pyright: ignore[reportAttributeAccessIssue]
    return render(request, "logbook/ascent_confirm_delete.html", {"ascent": ascent})


def gym_list(request: HttpRequest) -> HttpResponse:
    return render(request, "logbook/gym_list.html", {"gyms": Gym.objects.all()})


def _gym_form_view(
    request: HttpRequest, title: str, gym: Gym | None = None
) -> HttpResponse:
    form = GymForm(request.POST or None, instance=gym)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            # A concurrent request took the name between validation and save.
            form.add_error("name", "A Gym with that name already exists.")
        else:
            return redirect("gym_list")
    context = {"form": form, "title": title, "gym": gym}
    return render(request, "logbook/gym_form.html", context)


def gym_create(request: HttpRequest) -> HttpResponse:
    return _gym_form_view(request, "Add a Gym")


def gym_edit(request: HttpRequest, pk: int) -> HttpResponse:
    return _gym_form_view(request, "Edit Gym", get_object_or_404(Gym, pk=pk))


def gym_delete(request: HttpRequest, pk: int) -> HttpResponse:
    gym = get_object_or_404(Gym, pk=pk)
    refused = False
    if request.method == "POST":
        try:
            gym.delete()
        except ProtectedError:
            refused = True
        else:
            return redirect("gym_list")
    context = {"gym": gym, "refused": refused}
    status = 409 if refused else 200
    return render(request, "logbook/gym_confirm_delete.html", context, status=status)


def grade_options(request: HttpRequest) -> HttpResponse:
    """The grade <option>s for the chosen Route type and grade system."""
    choices = grade_choices(
        request.GET.get("route_type", ""), request.GET.get("grade_system", "")
    )
    return render(request, "logbook/_grade_options.html", {"choices": choices})
