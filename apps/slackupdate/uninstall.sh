#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute este desinstalador como root: sudo ./uninstall.sh" >&2
    exit 1
fi

rm -f /opt/slackupdate/app.py
rmdir /opt/slackupdate 2>/dev/null || true
rm -f /usr/bin/slackupdate
rm -f /usr/share/applications/slackupdate.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/slackupdate.svg

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi

echo "SlackUpdate removido. O histórico do usuário foi preservado."
