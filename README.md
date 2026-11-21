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
from `staticfiles/`; run `uv run python manage.py collectstatic` to populate it (the container image does this at build time, see below).

## Container image

```
docker build -t the-logbook .
docker run -d --name logbook --network the_logbook_default -p 127.0.0.1:8000:8000 \
  -e DJANGO_DEBUG=false -e DJANGO_SECRET_KEY=<secret> \
  -e DJANGO_ALLOWED_HOSTS=<hostname> -e DJANGO_CSRF_TRUSTED_ORIGINS=https://<hostname> \
  -e POSTGRES_HOST=db -e POSTGRES_PASSWORD=<password> the-logbook
```

The image runs gunicorn as a non-root user, applies migrations on every start (`python manage.py migrate`, so it needs a reachable database) and ships with
static files already collected. No secrets are baked in: everything comes from the
environment variables listed under Configuration, including `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PORT`. The port is bound to `127.0.0.1` so the app is only reachable from the host (Tailscale fronts it). The Compose production setup (#13) wires this together.

Create the login account in the running container (first run only):

```
docker exec -it logbook python manage.py createsuperuser
```
