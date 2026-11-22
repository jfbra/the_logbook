FROM python:3.14.10-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY manage.py ./
COPY config ./config
COPY logbook ./logbook
COPY docker-entrypoint.sh ./

# Collect static files at build time. These values exist only for this command
# and are not stored in the image environment.
RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=build-only POSTGRES_PASSWORD=build-only \
    python manage.py collectstatic --noinput

RUN useradd --system --create-home app \
    && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
