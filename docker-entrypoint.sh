#!/bin/sh
set -e

# Apply migrations, then hand over to the server command.
python manage.py migrate --noinput
exec "$@"