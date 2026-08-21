#!/usr/bin/env bash
# Render build script — runs once before the web service starts
set -o errexit   # exit immediately on any error

pip install --upgrade pip
pip install -r requirements.txt

# Collect all static files into staticfiles/
python manage.py collectstatic --no-input

# Apply any pending database migrations (includes Authentication 0002_pendingsignup)
python manage.py migrate --no-input

# Show applied migrations for visibility in Render build log
python manage.py showmigrations --no-input 2>/dev/null || true
