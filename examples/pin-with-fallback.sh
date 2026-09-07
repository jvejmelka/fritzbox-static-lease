#!/usr/bin/env bash
# Mit LLM „vibe-coded“, automatisch von Claude erstellt & veröffentlicht. Siehe PROVENANCE.md
#
# Beispiel: ein Gerät festnageln, mit automatischem Fallback über alle drei Kanäle.
#   [1] REST (api/v0)   – primär, ein HTTP-Request, kein Browser
#   [2] data.lua        – browserlos, falls AVM die REST-Route mal umbaut
#   [3] Playwright-UI   – letzte Rückfallebene (contrib/, braucht Chromium)
#
# Jeder Schreibweg verifiziert sich selbst kanalübergreifend (REST-GET + query.lua)
# und liefert Exit 0 nur bei bestätigtem Erfolg — deshalb reicht die Exit-Code-Kette.
#
# Voraussetzung (Zugangsdaten NUR über Umgebung, nie als Argument):
#   export FRITZ_USER="dein-box-benutzer"     # Benutzer mit Recht "FRITZ!Box-Einstellungen"
#   export FRITZ_PASSWORD="…"                 # sonst interaktiv abgefragt
#   export FRITZ_URL="http://fritz.box"       # optional, das ist der Default
#
# Aufruf:  examples/pin-with-fallback.sh <MAC|IP|Name>
#          (MAC ist der stabile Schlüssel — UIDs ändern sich beim Geräte-Reset)

set -euo pipefail
cd "$(dirname "$0")/.."                        # ins Repo-Wurzelverzeichnis
DEV="${1:?Aufruf: examples/pin-with-fallback.sh <MAC|IP|Name>}"

echo "[1/3] REST (api/v0) …"
if ./fritz_lease.py pin "$DEV"; then
    exit 0
fi

echo "[2/3] REST fehlgeschlagen — Fallback data.lua (browserlos) …"
if ./fritz_lease.py --via datalua pin "$DEV"; then
    exit 0
fi

echo "[3/3] data.lua fehlgeschlagen — letzte Rückfallebene Playwright-UI …"
# Playwright liest das Passwort aus stdin; URL/Benutzer als Argumente
printf '%s\n' "${FRITZ_PASSWORD:-}" | \
    python3 contrib/fritz_ui.py --url "${FRITZ_URL:-http://fritz.box}" \
                                --user "${FRITZ_USER:-}" pin "$DEV"

# ein Klick ist kein Speichern — unabhängig über REST/query.lua gegenlesen:
echo "→ Verifikation nach UI-Schreibweg:"
./fritz_lease.py verify "$DEV" --expect 1
