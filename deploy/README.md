# Deployment Guide — SelectRoyal Maids on AlmaLinux 9 + nginx

This guide deploys the **SelectRoyal Maids** Django site (`Django 6.1`, `gunicorn`,
`WhiteNoise` static, `nginx` reverse proxy) on a **AlmaLinux 9** VPS.

```
Browser ──▶ nginx :80/:443 ──► /static/, /media/  (served directly)
                    └──────────► /run/gunicorn.sock ──► gunicorn (Django WSGI)
```

---

## 1. Prerequisites

- AlmaLinux 9 VPS with a public IP pointing at **selectroyalmaids.com.ng**.
- Root or `sudo` access.
- **Python 3.12+ required** (Django 6.x). AlmaLinux 9 ships 3.9 by default, so we
  install a newer Python. Easiest reliable path is `pyenv`:

```bash
sudo dnf -y install gcc make patch zlib-devel bzip2 bzip2-devel readline-devel \
     sqlite sqlite-devel openssl openssl-devel tk-devel libffi-devel xz-devel git

# as your user:
curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
echo 'export PATH="$HOME/.pyenv/bin:$PATH"'    >> ~/.bashrc
echo 'eval "$(pyenv init -)"'                  >> ~/.bashrc
exec $SHELL -l
pyenv install 3.12.10          # or 3.13/3.14 — anything ≥ 3.12
pyenv global 3.12.10
python --version               # must print 3.12.x+
```

## 2. Install packages

```bash
sudo dnf -y install nginx git certbot python3-certbot-nginx policycoreutils-python-utils
sudo systemctl enable --now nginx
sudo systemctl enable certbot-renew.timer
sudo firewall-cmd --permanent --add-service=http --add-service=https
sudo firewall-cmd --reload
```

## 3. Create the app account and directories

```bash
sudo useradd --system --create-home --home-dir /srv/selectroyal --shell /sbin/nologin selectroyal
sudo mkdir -p /srv/selectroyal /etc/selectroyal
sudo git clone https://github.com/SAMUELNNAJI/SELECTROYALMAIDS.git /srv/selectroyal
sudo chown -R selectroyal:selectroyal /srv/selectroyal
```

Create the virtualenv **as the selectroyal user** (uses whichever python ≥ 3.12
is on your PATH above):

```bash
sudo -u selectroyal python3 -m venv /srv/selectroyal/venv
sudo -u selectroyal /srv/selectroyal/venv/bin/pip install --upgrade pip
sudo -u selectroyal /srv/selectroyal/venv/bin/pip install -r /srv/selectroyal/requirements.txt
```

## 4. Production environment file

```bash
sudo cp /srv/selectroyal/deploy/selectroyal.env.example /etc/selectroyal/selectroyal.env
sudo chown root:selectroyal /etc/selectroyal/selectroyal.env
sudo chmod 640 /etc/selectroyal/selectroyal.env
sudo vi /etc/selectroyal/selectroyal.env
```

Fill in **at minimum**:
- `SECRET_KEY` → `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `ALLOWED_HOSTS` → your domain + server IP
- `DATABASE_URL` → your Postgres connection string (Neon etc.). If left empty the
  site falls back to SQLite at `/srv/selectroyal/db.sqlite3`.
- `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `NOTIFICATION_EMAIL`
  (`info@selectroyalmaids.com.ng` is the default — this is where new
  "Request a Maid" placement requests **and** "Register as a Maid" applications
  are emailed).
- `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` — required for Maid
  registration forms to be delivered via WhatsApp to `WHATSAPP_APPLICATION_RECIPIENT`
  (`+234 913 789 4958`, already configured).
- `FLUTTERWAVE_*` live keys and `SITE_URL=https://selectroyalmaids.com.ng`.

## 5. Install systemd units (gunicorn behind a unix socket)

```bash
sudo cp /srv/selectroyal/deploy/gunicorn.service /etc/systemd/system/
sudo cp /srv/selectroyal/deploy/gunicorn.socket  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn.socket
sudo systemctl start gunicorn.service
# Wait ~2s then confirm the socket exists and the app responds:
sudo systemctl status gunicorn.socket
ls -l /run/gunicorn.sock
curl --unix-socket /run/gunicorn.sock http://localhost/ -o /dev/null -w '%{http_code}\n'   # → 200
```

## 6. nginx configuration

```bash
sudo cp /srv/selectroyal/deploy/nginx-selectroyalmaids.conf /etc/nginx/conf.d/selectroyalmaids.conf
sudo sed -i 's/^\(user\).*/\1 nginx;/' /etc/nginx/nginx.conf   # ensure nginx user is `nginx`
sudo nginx -t && sudo systemctl reload nginx
```

### SELinux (AlmaLinux ships with SELinux enforcing)

```bash
# allow nginx to talk to the gunicorn unix socket over httpd_can_network_connect
sudo setsebool -P httpd_can_network_connect 1
# label the site files so nginx can read static/media
sudo chcon -R -t httpd_sys_content_t /srv/selectroyal
sudo setsebool -P httpd_read_user_content 1
```

## 7. HTTPS with Let's Encrypt

```bash
sudo certbot --nginx -d selectroyalmaids.com.ng -d www.selectroyalmaids.com.ng
# certbot edits the nginx server block automatically; follow the HTTPS redirect prompt
sudo certbot renew --dry-run    # verify auto-renewal works
```

## 8. Initial database & admin

```bash
sudo -u selectroyal /srv/selectroyal/venv/bin/python /srv/selectroyal/manage.py migrate --noinput
sudo -u selectroyal /srv/selectroyal/venv/bin/python /srv/selectroyal/manage.py collectstatic --noinput
sudo -u selectroyal /srv/selectroyal/venv/bin/python /srv/selectroyal/manage.py createsuperuser
sudo systemctl restart gunicorn
```

Your site is live at `https://selectroyalmaids.com.ng`, admin at `/admin/`,
and every new **Request a Maid** submission is emailed to
`info@selectroyalmaids.com.ng` as well as stored in the employer's support chat.

## 9. Deploying future updates

```bash
sudo bash /srv/selectroyal/deploy/deploy.sh
```

The script pulls `origin/main`, installs requirements, migrates, collects static
files, restarts gunicorn, and reloads nginx.

## 10. Adding a SECOND Django site to the same VPS (e.g. getmecare-ontario.com)

You can host multiple Django sites on this server. Each one gets its **own**
folder, system user, socket, and nginx server block — nginx picks the right app
by domain name (`server_name`).

### Fastest way — one-shot scaffold script

```bash
# copy the script onto the VPS once (or clone this repo there):
sudo bash /srv/selectroyal/deploy/add-new-site.sh \
    getmecare \
    getmecare-ontario.com \
    https://github.com/YOUR/GETMECARE.git \
    python3.12 \
    getmecare.wsgi:application
```

Then follow the 4 steps it prints at the end (env file → migrate/collectstatic →
certbot → verify). The script:
- creates system user `getmecare` + clones code to `/srv/getmecare`
- creates venv and installs `requirements.txt`
- writes `/etc/getmecare/getmecare.env` (or copies your repo's `.env.example`)
- installs `gunicorn-getmecare.{service,socket}` on socket `/run/gunicorn-getmecare.sock`
- writes `/etc/nginx/conf.d/getmecare-ontario.com.conf`
- starts services, reloads nginx, labels SELinux

### Manual alternative (what the script does step-by-step)

```bash
# 1) App account, folder, clone — SAME server, NEW folder per site
sudo useradd --system --create-home --home-dir /srv/getmecare --shell /sbin/nologin getmecare
sudo git clone https://github.com/YOUR-USER/GETMECARE.git /srv/getmecare
sudo chown -R getmecare:getmecare /srv/getmecare

# 2) venv (python 3.12+)
sudo -u getmecare python3.12 -m venv /srv/getmecare/venv
sudo -u getmecare /srv/getmecare/venv/bin/pip install -r /srv/getmecare/requirements.txt

# 3) env file (own /etc/<site>/ folder)
sudo mkdir -p /etc/getmecare
sudo cp /srv/getmecare/.env.example /etc/getmecare/getmecare.env
sudo chown root:getmecare /etc/getmecare/getmecare.env && sudo chmod 640 /etc/getmecare/getmecare.env

# 4) systemd units — new unit name + new socket so it won't clash with gunicorn
sudo cp deploy/gunicorn.service  /etc/systemd/system/gunicorn-getmecare.service
sudo cp deploy/gunicorn.socket   /etc/systemd/system/gunicorn-getmecare.socket
sudo sed -i 's#/srv/selectroyal#/srv/getmecare#g; s#gunicorn.sock#gunicorn-getmecare.sock#g' /etc/systemd/system/gunicorn-getmecare.*
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-getmecare.socket
sudo systemctl start gunicorn-getmecare.service

# 5) nginx — own server block; keep the existing selectroyalmaids one untouched
sudo cp deploy/nginx-selectroyalmaids.conf /etc/nginx/conf.d/getmecare-ontario.com.conf
sudo sed -i 's/selectroyalmaids\.com\.ng/getmecare-ontario.com/g; s#/srv/selectroyal#/srv/getmecare#g; s#gunicorn\.sock#gunicorn-getmecare.sock#g' /etc/nginx/conf.d/getmecare-ontario.com.conf
sudo nginx -t && sudo systemctl reload nginx

# 6) HTTPS (point DNS at this server first)
sudo certbot --nginx -d getmecare-ontario.com -d www.getmecare-ontario.com
```

### Notes when running two sites side-by-side

- **`ALLOWED_HOSTS`** in `/etc/getmecare/getmecare.env` must contain
  `getmecare-ontario.com` (and `www.…`); the other site's env is untouched.
- **Sockets are unique** per site: `/run/gunicorn.sock` (selectroyal) and
  `/run/gunicorn-getmecare.sock` (getmecare) — never share one socket.
- **SELinux** once-off per new site: `sudo chcon -R -t httpd_sys_content_t /srv/getmecare`
  and `sudo setsebool -P httpd_can_network_connect 1` (already enabled for the first site).
- **Firewall** already allows 80/443 — nothing to change.
- Future updates: adapt a copy of `deploy.sh` for the new site (change
  `APP_DIR`, `UNIT`, `ENV_FILE`), or just re-run migrate/collectstatic +
  `systemctl restart gunicorn-getmecare`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 Bad Gateway` | `sudo systemctl status gunicorn.socket gunicorn`; `sudo journalctl -u gunicorn -f`; check `/run/gunicorn.sock` exists and group is `nginx` |
| SELinux blocking nginx→socket | `sudo setsebool -P httpd_can_network_connect 1` (see step 6) |
| Am I seeing the HTTPS redirect loop | Ensure nginx sets `X-Forwarded-Proto $scheme` (already in the template) |
| 400 Bad Request (DisallowedHost) | Add the domain to `ALLOWED_HOSTS` in `/etc/selectroyal/selectroyal.env`, then `systemctl restart gunicorn` |
| Uploads too large | Raise `client_max_body_size` in nginx conf and restart nginx |