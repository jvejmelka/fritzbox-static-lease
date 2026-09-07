#!/usr/bin/env bash
# Mit LLM „vibe-coded“, automatisch von Claude erstellt & veröffentlicht. Siehe PROVENANCE.md
#
# DEMO: alle sechs Wege einmal sichtbar ausführen —
#   3 Schreibkanäle:  REST (api/v0) · data.lua · Playwright-UI
#   3 Leser/Prüfer:   REST-GET · query.lua · Playwright-UI (kalter Leseabruf)
#
# ⚠️ Nur auf einem EIGENEN Testgerät laufen lassen: es wird mehrfach ent- und
#    festgepinnt. Der Schritt „--via datalua“ kann bei einem Gerät mit gesetztem
#    Zugangsprofil dieses Profil berühren (siehe CLAUDE.md, offene Punkte) — auf
#    einem Standard-Gerät unkritisch.
#
# Voraussetzung (Zugangsdaten nur über Umgebung):
#   export FRITZ_USER="dein-box-benutzer"
#   export FRITZ_PASSWORD="…"
#   export FRITZ_URL="http://fritz.box"     # optional
#
# Aufruf:  examples/demo-alle-kanaele.sh <MAC|IP|Name>

set -euo pipefail
cd "$(dirname "$0")/.."
DEV="${1:?Aufruf: examples/demo-alle-kanaele.sh <MAC|IP|Name>}"
UI() { printf '%s\n' "${FRITZ_PASSWORD:-}" | python3 contrib/fritz_ui.py \
         --url "${FRITZ_URL:-http://fritz.box}" --user "${FRITZ_USER:-}" "$@"; }

echo "=================== SCHREIBKANÄLE ==================="

echo "[Schreiben 1] REST (api/v0) — inkl. Selbstprüfung REST-GET + query.lua:"
./fritz_lease.py unpin "$DEV" >/dev/null
./fritz_lease.py pin "$DEV"

echo "[Schreiben 2] data.lua (browserlos):"
./fritz_lease.py unpin "$DEV" >/dev/null
./fritz_lease.py --via datalua pin "$DEV"

echo "[Schreiben 3] Playwright-UI (headless, Tab „Heimnetz“):"
./fritz_lease.py unpin "$DEV" >/dev/null
UI pin "$DEV"

echo "=================== LESER / PRÜFER ==================="

echo "[Lesen 1+2] REST-GET UND query.lua (kanalübergreifend in verify):"
./fritz_lease.py verify "$DEV" --expect 1

echo "[Lesen 3] Playwright-UI — kalter Leseabruf, ändert nichts:"
UI read "$DEV"

echo "===================================================="
echo "Alle sechs Wege ausgeführt. Endzustand: static_dhcp=1."
