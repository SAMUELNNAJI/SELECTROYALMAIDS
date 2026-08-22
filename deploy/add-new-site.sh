#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# add-new-site.sh — scaffold a brand-new Django site on this AlmaLinux VPS,
# alongside any existing sites (nginx reverse proxy, gunicorn via systemd).
#
# Run with sudo ON THE VPS (this is a one-time scaffolding step):
#
#   sudo bash /path/to/add-new-site.sh \
#       getmecare \
#       getmecare-ontario.com \
#       https://github.com/YOUR/GETMECARE.git \
#       python3.12 \
#       getmecare.wsgi:application
#
#   arg1 = site/account short name        (getmecare)
#   arg2 = domain                         (getmecare-ontario.com)
#   arg3 = git clone URL for the code     (https://github.com/YOUR/GETMECARE.git)
#   arg4 = system python >= 3.12          (python3.12)
#   arg5 = your WSGI module               (getmecare.wsgi:application)
#
# After it finishes:
#   1. vi /etc/getmecare/getmecare.env      (SECRET_KEY, ALLOWED_HOSTS, …)
#   2. migrate + collectstatic + createsuperuser  (see final printed block)
#   3. Get an SSL certificate:  sudo certbot --nginx -d getmecare-ontario.com
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SITE_NAME="${1:?Usage: $0 SITE_NAME DOMAIN GIT_URL [PYTHON_BIN] [WSGI_MODULE]}"
DOMAIN="${2:?Usage: $0 SITE_NAME DOMAIN GIT_URL [PYTHON_BIN] [WSGI_MODULE]}"
GIT_URL="${3:?Usage: $0 SITE_NAME DOMAIN GIT_URL [PYTHON_BIN] [WSGI_MODULE]}"
PYTHON_BIN="${4:-python3.12}"
WSGI_MODULE="${5:-config.wsgi:application}"

APP_DIR="/srv/${SITE_NAME}"
VENV_DIR="${APP_DIR}/venv"
ENV_DIR="/etc/${SITE_NAME}"
ENV_FILE="${ENV_DIR}/${SITE_NAME}.env"
SOCKET_FILE="/run/gunicorn-${SITE_NAME}.sock"
NGINX_CONF="/etc/nginx/conf.d/${DOMAIN}.conf"
UNIT_NAME="gunicorn-${SITE_NAME}"

if id "${SITE_NAME}" &>/dev/null; then
    echo "✗ system user '${SITE_NAME}' already exists — aborting." >&2
    exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "✗ python not found: ${PYTHON_BIN} — install Python 3.12+ first." >&2
    exit 1
fi

echo "▶ 1/8 System user + checkout of ${GIT_URL}"
# Create the system user WITHOUT a home skeleton. On AlmaLinux, `adduser --create-home`
# populates the new folder with /etc/skel dotfiles (.bashrc, .bash_profile…), which would
# make the git clone target NON-EMPTY and cause `git clone` to refuse.
# So we create the app folder ourselves (empty), verify it, then clone into it.
adduser --system --no-create-home --home-dir "${APP_DIR}" --shell /sbin/nologin "${SITE_NAME}"
mkdir -p "${APP_DIR}"
if [[ -n "$(ls -A "${APP_DIR}")" ]]; then
    echo "✗ ${APP_DIR} already exists and is not empty — refusing to overwrite." >&2
    exit 1
fi
git clone "${GIT_URL}" "${APP_DIR}"
chown -R "${SITE_NAME}:${SITE_NAME}" "${APP_DIR}"

echo "▶ 2/8 Python virtualenv"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
chown -R "${SITE_NAME}:${SITE_NAME}" "${VENV_DIR}"
sudo -u "${SITE_NAME}" "${VENV_DIR}/bin/pip" install --upgrade pip
sudo -u "${SITE_NAME}" "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "▶ 3/8 Environment file ${ENV_FILE}"
mkdir -p "${ENV_DIR}"
if [[ -f "${APP_DIR}/deploy/${SITE_NAME}.env.example" ]]; then
    cp "${APP_DIR}/deploy/${SITE_NAME}.env.example" "${ENV_FILE}"
elif [[ -f "${APP_DIR}/.env.example" ]]; then
    cp "${APP_DIR}/.env.example" "${ENV_FILE}"
else
    cat > "${ENV_FILE}" <<EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=False
ALLOWED_HOSTS=${DOMAIN} www.${DOMAIN}
DATABASE_URL=
EOF
fi
chown root:"${SITE_NAME}" "${ENV_FILE}"
chmod 640 "${ENV_FILE}"

echo "▶ 4/8 systemd units (socket + service)"
cat > "/etc/systemd/system/${UNIT_NAME}.socket" <<EOF
[Unit]
Description=gunicorn socket for ${SITE_NAME}
PartOf=${UNIT_NAME}.service

[Socket]
ListenStream=${SOCKET_FILE}
SocketUser=nginx
SocketGroup=nginx
SocketMode=0660

[Install]
WantedBy=sockets.target
EOF

cat > "/etc/systemd/system/${UNIT_NAME}.service" <<EOF
[Unit]
Description=gunicorn daemon for ${SITE_NAME} (Django WSGI)
Requires=${UNIT_NAME}.socket
After=network.target ${UNIT_NAME}.socket

[Service]
User=${SITE_NAME}
Group=${SITE_NAME}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn \\
    --workers 3 \\
    --timeout 120 \\
    --access-logfile - \\
    --error-logfile - \\
    --capture-output \\
    ${WSGI_MODULE}
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
KillSignal=SIGQUIT
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=${APP_DIR}

[Install]
WantedBy=multi-user.target
EOF

echo "▶ 5/8 nginx server block: ${NGINX_CONF}"
cat > "${NGINX_CONF}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};

    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 20m;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    location /media/ {
        alias ${APP_DIR}/media/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }
    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_pass http://unix:${SOCKET_FILE};
        proxy_read_timeout 120;
    }
}
EOF

echo "▶ 6/8 Start services"
systemctl daemon-reload
systemctl enable --now "${UNIT_NAME}.socket"
systemctl start "${UNIT_NAME}.service"

echo "▶ 7/8 SELinux + nginx"
chcon -R -t httpd_sys_content_t "${APP_DIR}" 2>/dev/null || true

# If not signed yet, install a temporary self-signed cert so `nginx -t` passes.
# Real Let's Encrypt certs are obtained later with certbot --nginx.
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
if [[ ! -f "${CERT_DIR}/fullchain.pem" || ! -f "${CERT_DIR}/privkey.pem" ]]; then
    echo "  → No Let's Encrypt cert yet — installing temp self-signed cert for ${DOMAIN}"
    mkdir -p "${CERT_DIR}"
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "${CERT_DIR}/privkey.pem" \
        -out "${CERT_DIR}/fullchain.pem" \
        -days 30 -subj "/CN=${DOMAIN}" 2>/dev/null
fi
nginx -t && systemctl reload nginx

echo "▶ 8/8 Final manual steps"
cat <<NEXT
✔ Scaffold for ${DOMAIN} is ready in ${APP_DIR}.

1) Point DNS of ${DOMAIN} at this server, then set environment:
     sudo vi ${ENV_FILE}
   (SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, SMTP credentials…)

2) First-time DB + static files:
     sudo -u ${SITE_NAME} ${VENV_DIR}/bin/python ${APP_DIR}/manage.py migrate --noinput
     sudo -u ${SITE_NAME} ${VENV_DIR}/bin/python ${APP_DIR}/manage.py collectstatic --noinput
     sudo -u ${SITE_NAME} ${VENV_DIR}/bin/python ${APP_DIR}/manage.py createsuperuser
     sudo systemctl restart ${UNIT_NAME}.service

3) HTTPS:
     sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}
     sudo certbot renew --dry-run

4) Verify it answers:
     curl -I https://${DOMAIN}
NEXT