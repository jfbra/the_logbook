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

## Continuous integration

GitHub Actions (`.github/workflows/ci.yml`) runs on every pull request and every push to `master`, with no path filters. It installs dependencies exactly from `uv.lock`, then runs ruff lint, ruff format check, pyright and the full test suite against a `postgres:17` service container. Run the same checks locally (with `docker compose up -d db` running):

```
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

A second job, "Production image builds", runs `docker build .` on every run to prove the production image still builds. It does not push the image anywhere. Run it locally with `docker build .`.

CI uses the Python version in `.python-version` and uv 0.13.9 (the same uv as the Dockerfile; update both together). Third-party actions are pinned to full commit SHAs, with the version in a comment.

## Configuration

Development needs no environment variables. Production sets these:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `true` | Set to `false` in production. |
| `DJANGO_SECRET_KEY` | dev-only value when debug is on | **Required** when `DJANGO_DEBUG=false`; the app refuses to start if it is empty or `change-me`. |
| `DJANGO_ALLOWED_HOSTS` | empty | Comma-separated hostnames, e.g. `logbook.tailnet-name.ts.net`. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins including scheme, e.g. `https://logbook.tailnet-name.ts.net`. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `logbook` | Database credentials. In production the password is **required** and must not be empty, `change-me` or `logbook`. |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `127.0.0.1`, `5432` | Database location. `127.0.0.1` rather than `localhost` because the Compose database port is bound to IPv4 loopback only. |

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
environment variables listed under Configuration, including `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PORT`. The port is bound to `127.0.0.1` so the app is only reachable from the host (Tailscale fronts it). For normal deployment use the Compose setup below instead of `docker run`.

Create the login account in the running container (first run only):

```
docker exec -it logbook python manage.py createsuperuser
```

## Production with Docker Compose

One Compose file runs both workflows. In development you start only the database
(`docker compose up -d db`). In production it runs the app and Postgres together:

```
cp .env.example .env         # then edit .env: secret key, hostname, database password
docker compose up -d --build
docker compose exec app python manage.py createsuperuser   # first run only
```

- `.env` is git-ignored; `.env.example` documents every variable you set. Compose fixes
  `DJANGO_DEBUG`, `POSTGRES_HOST` and `POSTGRES_PORT` for the app, so they are not in it.
- Keep the real `.env` on the server only. Every `docker compose` command reads it, so on a
  dev machine it would change the development database's credentials.
- Set a real `POSTGRES_PASSWORD` before the first `up`. Postgres ignores a changed password
  on an existing volume. If you started without one, run `docker compose down -v` (fresh
  installs only: it deletes the data) and start again.
- The Postgres port (`127.0.0.1:5432`) is published only so development can use `uv run`;
  production does not need it.
- The app (`127.0.0.1:8000`) and Postgres (`127.0.0.1:5432`) are bound to the host only, so
  nothing is published to the network. Tailscale serve fronts the app (see #14).
- The stack always runs the app with `DJANGO_DEBUG=false`. If `DJANGO_SECRET_KEY` is missing
  the app container exits with an `ImproperlyConfigured` error (see `docker compose logs app`).
- Postgres data lives in the `pgdata` volume, so it survives `docker compose down`, image
  rebuilds and redeploys. `docker compose down -v` deletes it, so don't use `-v` in production.
- Port 8000 or 5432 already in use on the host (for example a local `runserver`)? Stop that
  first, because the ports are fixed.
