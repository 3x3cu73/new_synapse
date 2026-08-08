#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_HOST="${VM_HOST:-azureuser@98.70.40.108}"
REMOTE_DIR="${REMOTE_DIR:-/opt/synapse}"
WEB_ROOT="${WEB_ROOT:-/var/www/synapse}"
DOMAIN="${DOMAIN:-synapse.devclub.in}"

echo "Ensuring remote directories exist"
ssh "${VM_HOST}" "sudo mkdir -p ${REMOTE_DIR} ${WEB_ROOT} ${REMOTE_DIR}/uploads && sudo chown -R \$(whoami):\$(whoami) ${REMOTE_DIR} ${WEB_ROOT}"

echo "Syncing to ${VM_HOST}:${REMOTE_DIR}"
rsync -az --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'frontend/build' \
  --exclude 'frontend/dist' \
  --exclude 'backend/.venv' \
  --exclude 'backend/.env' \
  --exclude 'uploads' \
  --exclude 'backend/static/uploads' \
  -e ssh \
  "${ROOT_DIR}/" "${VM_HOST}:${REMOTE_DIR}/"

if [[ -f "${ROOT_DIR}/backend/.env" ]]; then
  echo "Uploading backend/.env"
  rsync -az -e ssh "${ROOT_DIR}/backend/.env" "${VM_HOST}:${REMOTE_DIR}/backend/.env"
  ssh "${VM_HOST}" "chmod 600 ${REMOTE_DIR}/backend/.env"
fi

ssh "${VM_HOST}" bash -s <<EOF
set -euo pipefail
mkdir -p ${REMOTE_DIR}/uploads

# Ensure Postgres database exists (non-destructive)
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='synapse_app'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE synapse_app OWNER caic;"

cd ${REMOTE_DIR}/backend
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python init_db.py
.venv/bin/python -c 'from app.main import app; print("App import OK")'

sudo cp ${REMOTE_DIR}/deploy/systemd/synapse-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable synapse-api
sudo systemctl restart synapse-api
sleep 2
curl -fsS http://127.0.0.1:8011/api/health

cd ${REMOTE_DIR}/frontend
npm ci
npm run build
sudo mkdir -p ${WEB_ROOT}
sudo rsync -a --delete build/ ${WEB_ROOT}/

sudo cp ${REMOTE_DIR}/deploy/nginx/synapse.conf /etc/nginx/sites-available/synapse.conf
sudo ln -sfn /etc/nginx/sites-available/synapse.conf /etc/nginx/sites-enabled/synapse.conf
sudo nginx -t
sudo systemctl reload nginx
EOF

echo "Deploy complete."
echo "Live check:"
curl -fsS "https://${DOMAIN}/api/health" || true
echo
echo "Site: https://${DOMAIN}"
