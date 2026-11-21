from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static

from .forms import SessionForm
from .models import Session
from .weekly import weekly_totals


def session_list(request: HttpRequest) -> HttpResponse:
    this_week, last_week = weekly_totals()
    context = {
        "sessions": Session.objects.all(),
        "this_week_minutes": this_week,
        "last_week_minutes": last_week,
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


@login_not_required
def manifest(request: HttpRequest) -> JsonResponse:
    """Web app manifest so the phone can install the app. No service worker."""
    data = {
        "name": "The Logbook",
        "short_name": "Logbook",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#1f2937",
        "theme_color": "#1f2937",
        "icons": [
            {
                "src": static("logbook/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": static("logbook/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")
