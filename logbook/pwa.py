from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, JsonResponse
from django.templatetags.static import static

THEME_COLOUR = "#1f2937"


def theme(request: HttpRequest) -> dict[str, str]:
    """Context processor so templates share the manifest's theme colour."""
    return {"theme_colour": THEME_COLOUR}


@login_not_required
def manifest(request: HttpRequest) -> JsonResponse:
    """Web app manifest so the phone can install the app. No service worker."""
    data = {
        "name": "The Logbook",
        "short_name": "Logbook",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": THEME_COLOUR,
        "theme_color": THEME_COLOUR,
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
