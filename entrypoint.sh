#!/bin/sh
set -e

# Apply database migrations and seed default roles before starting the API.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  flask db upgrade
  python - <<'PY'
from app import create_app
from app.services.role_service import RoleService

app = create_app()
with app.app_context():
    RoleService.ensure_default_roles()
PY
fi

exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --timeout ${GUNICORN_TIMEOUT:-120} app:app
