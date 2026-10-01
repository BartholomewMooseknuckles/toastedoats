#!/usr/bin/env bash
# install.sh - put the Toasted Oats site on this server. Idempotent: run it after every
# `git pull` and it copies the new code, updates dependencies, and restarts the service.
#
#   sudo /opt/toastedoats/install.sh
#
# Layout it creates (code is a copy, so the git checkout can live anywhere):
#   /opt/oats/app/oats    the package, as served
#   /opt/oats/venv        Flask + gunicorn
#   /opt/oats/oats.env    per-machine settings (created from oats.env.example, never overwritten)
#   /opt/oats/oats.db     signups and pre-orders
#   /opt/oats/backup/     nightly copies of the database
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO/oats"
DEST="${OATS_DEST:-/opt/oats}"
SVC_USER="${OATS_USER:-newsfeed}"
UNIT=toasted-oats

if [ "$(id -u)" -ne 0 ]; then
  echo "run with sudo" >&2
  exit 1
fi
if ! id "$SVC_USER" >/dev/null 2>&1; then
  echo "creating system user $SVC_USER"
  useradd --system --home "$DEST" --shell /usr/sbin/nologin "$SVC_USER"
fi

mkdir -p "$DEST/app" "$DEST/backup"

# the package, minus what the server never needs
rm -rf "$DEST/app/oats.new"
mkdir -p "$DEST/app/oats.new"
tar -C "$SRC" --exclude='./dist' --exclude='./tests' --exclude='./__pycache__' \
    --exclude='*.pyc' --exclude='./*.db*' -cf - . | tar -C "$DEST/app/oats.new" -xf -
rm -rf "$DEST/app/oats"
mv "$DEST/app/oats.new" "$DEST/app/oats"

# python
if [ ! -x "$DEST/venv/bin/python" ]; then
  python3 -m venv "$DEST/venv"
fi
"$DEST/venv/bin/pip" install -q --disable-pip-version-check -r "$REPO/requirements.txt"

# settings: created once, then yours
if [ ! -f "$DEST/oats.env" ]; then
  cp "$REPO/oats.env.example" "$DEST/oats.env"
  chmod 600 "$DEST/oats.env"
  echo "created $DEST/oats.env - check OATS_PUBLIC_ORIGIN and OATS_PORT"
fi

chown -R "$SVC_USER:$SVC_USER" "$DEST"

# database (as the service user, with the service's settings; the package must be on the path)
cd "$DEST/app"
sudo -u "$SVC_USER" env $(grep -v '^#' "$DEST/oats.env" | grep '=' | xargs) \
  "$DEST/venv/bin/python" -m oats init-db >/dev/null

# units
install -m 644 "$REPO/systemd/$UNIT.service" "$REPO/systemd/$UNIT-backup.service" \
               "$REPO/systemd/$UNIT-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now "$UNIT-backup.timer" >/dev/null

if systemctl is-enabled --quiet "$UNIT" 2>/dev/null; then
  systemctl restart "$UNIT"
  sleep 1
  systemctl --no-pager --lines=3 status "$UNIT" || true
else
  cat <<EOF

installed. next:
  1. edit $DEST/oats.env         (OATS_PUBLIC_ORIGIN, OATS_PORT)
  2. systemctl enable --now $UNIT
  3. curl -s 127.0.0.1:\$OATS_PORT/healthz
  4. add the Cloudflare tunnel rule - see HANDOFF.md
EOF
fi
