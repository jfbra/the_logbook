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
