#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute este instalador como root: sudo ./install.sh" >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

install -d /opt/slackupdate
install -m 0755 "$SCRIPT_DIR/app.py" /opt/slackupdate/app.py
install -m 0755 "$SCRIPT_DIR/slackupdate" /usr/bin/slackupdate
install -d /usr/share/applications
install -m 0644 "$SCRIPT_DIR/slackupdate.desktop" /usr/share/applications/slackupdate.desktop
install -d /usr/share/icons/hicolor/scalable/apps
install -m 0644 "$SCRIPT_DIR/slackupdate.svg" /usr/share/icons/hicolor/scalable/apps/slackupdate.svg

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi

echo "SlackUpdate instalado. Procure por SlackUpdate no menu Sistema."
