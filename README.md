# The Logbook

Personal training logbook. See `CONTEXT.md` for vocabulary and `docs/adr/` for decisions.

## Development

```
docker compose up -d db      # start Postgres
uv run python manage.py migrate
uv run python manage.py createsuperuser   # create your single login account (first run only)
uv run python manage.py runserver
```

## Tests

Requires the Compose Postgres to be running.

```
uv run pytest
```

## Configuration

Development needs no environment variables. Production sets these:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `true` | Set to `false` in production. |
| `DJANGO_SECRET_KEY` | dev-only value when debug is on | **Required** when `DJANGO_DEBUG=false`; the app refuses to start without it. |
| `DJANGO_ALLOWED_HOSTS` | empty | Comma-separated hostnames, e.g. `logbook.tailnet-name.ts.net`. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins including scheme, e.g. `https://logbook.tailnet-name.ts.net`. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `logbook` | Database credentials. |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `localhost`, `5432` | Database location. |

With `DJANGO_DEBUG=false`, session and CSRF cookies are marked secure and the app trusts
`X-Forwarded-Proto` from the proxy (Tailscale serve). Static files are served by WhiteNoise
from `staticfiles/`; run `uv run python manage.py collectstatic` to populate it.
