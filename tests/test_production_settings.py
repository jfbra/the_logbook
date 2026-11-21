import json
import os
import subprocess
import sys

from django.core.management import call_command
from django.test import Client

from .helpers import get

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = (
    "import json; from django.conf import settings; "
    "print(json.dumps({k: getattr(settings, k) for k in "
    "['DEBUG','ALLOWED_HOSTS','CSRF_TRUSTED_ORIGINS','SESSION_COOKIE_SECURE',"
    "'CSRF_COOKIE_SECURE','SECURE_PROXY_SSL_HEADER']}))"
)


def load_settings(**env: str) -> subprocess.CompletedProcess[str]:
    """Import config.settings in a fresh interpreter with exactly this environment."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_",))}
    clean.update(env)
    clean["DJANGO_SETTINGS_MODULE"] = "config.settings"
    return subprocess.run(
        [sys.executable, "-c", DUMP],
        cwd=REPO_ROOT,
        env=clean,
        capture_output=True,
        text=True,
    )


def test_production_refuses_to_start_without_a_secret_key():
    result = load_settings(DJANGO_DEBUG="false")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_development_starts_with_no_environment_set():
    result = load_settings()

    assert result.returncode == 0
    assert json.loads(result.stdout)["DEBUG"] is True


def test_production_settings_come_from_the_environment():
    result = load_settings(
        DJANGO_DEBUG="false",
        DJANGO_SECRET_KEY="s3cret",
        DJANGO_ALLOWED_HOSTS="logbook.tail1234.ts.net, localhost",
        DJANGO_CSRF_TRUSTED_ORIGINS="https://logbook.tail1234.ts.net",
    )

    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    assert loaded["DEBUG"] is False
    assert loaded["ALLOWED_HOSTS"] == ["logbook.tail1234.ts.net", "localhost"]
    assert loaded["CSRF_TRUSTED_ORIGINS"] == ["https://logbook.tail1234.ts.net"]


def test_production_cookies_are_secure_and_proxy_https_is_trusted():
    result = load_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY="s3cret")

    loaded = json.loads(result.stdout)
    assert loaded["SESSION_COOKIE_SECURE"] is True
    assert loaded["CSRF_COOKIE_SECURE"] is True
    assert loaded["SECURE_PROXY_SSL_HEADER"] == ["HTTP_X_FORWARDED_PROTO", "https"]


def test_development_cookies_work_over_plain_http():
    loaded = json.loads(load_settings().stdout)

    assert loaded["SESSION_COOKIE_SECURE"] is False
    assert loaded["CSRF_COOKIE_SECURE"] is False
    assert loaded["SECURE_PROXY_SSL_HEADER"] is None


def test_static_files_and_icons_are_served_after_collectstatic(settings, tmp_path):
    settings.DEBUG = False
    settings.WHITENOISE_USE_FINDERS = False  # prove it's collectstatic output
    settings.WHITENOISE_AUTOREFRESH = False
    settings.STATIC_ROOT = tmp_path
    call_command("collectstatic", interactive=False, verbosity=0)

    css = get(Client(), "/static/logbook/app.css")
    icon = get(Client(), "/static/logbook/icon-192.png")

    assert css.status_code == 200
    assert icon.status_code == 200


def test_production_refuses_an_empty_secret_key():
    # Compose passes an unset DJANGO_SECRET_KEY through as an empty string.
    result = load_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY="")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr
