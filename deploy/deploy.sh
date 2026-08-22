#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# SelectRoyal Maids — deploy script for AlmaLinux VPS (run with sudo)
#
#   sudo bash /srv/selectroyal/deploy/deploy.sh
#
# Assumes (see deploy/README.md):
#   - app checked out at /srv/selectroyal (owner: selectroyal)
#   - virtualenv at /srv/selectroyal/venv
#   - env file at /etc/selectroyal/selectroyal.env
#   - systemd units gunicorn.service / gunicorn.socket already installed
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/srv/selectroyal"
VENV="$APP_DIR/venv"
PY="$VENV/bin/python"
ENV_FILE="/etc/selectroyal/selectroyal.env"

if [[ ! -d "$APP_DIR/.git" ]]; then
    echo "✗ $APP_DIR is not a git checkout" >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "✗ $ENV_FILE missing — copy deploy/selectroyal.env.example first" >&2
    exit 1
fi

cd "$APP_DIR"
echo "▶ Pulling latest code…"
sudo -u selectroyal git fetch --all --prune
sudo -u selectroyal git reset --hard origin/main

echo "▶ Installing Python dependencies…"
sudo -u selectroyal "$VENV/bin/pip" install --upgrade pip
sudo -u selectroyal "$VENV/bin/pip" install -r requirements.txt

echo "▶ Applying database migrations…"
sudo -u selectroyal "$VENV/bin/python" manage.py migrate --noinput

echo "▶ Collecting static files…"
sudo -u selectroyal "$VENV/bin/python" manage.py collectstatic --noinput

echo "▶ Production sanity check…"
sudo -u selectroyal "$VENV/bin/python" manage.py check --deploy --fail-level WARNING || echo "  (warnings above are advisory only)"

echo "▶ Restarting gunicorn…"
sudo systemctl restart gunicorn.service

echo "▶ Reloading nginx…"
sudo nginx -t && sudo systemctl reload nginx

echo "✔ Deployment complete: https://selectroyalmaids.com.ng"
echo "  Logs:  journalctl -u gunicorn -f | tail"
echo "  Status: systemctl status gunicorn"