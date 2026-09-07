#!/usr/bin/env bash
# Mit LLM „vibe-coded“, automatisch von Claude erstellt & veröffentlicht. Siehe PROVENANCE.md
#
# Beispiel: ein Gerät festnageln, mit automatischem Fallback über alle drei Schreibkanäle.
#   [1] REST (api/v0)   – primär, ein HTTP-Request, kein Browser
#   [2] data.lua        – browserlos, falls AVM die REST-Route mal umbaut
#   [3] Playwright-UI   – letzte Rückfallebene (contrib/, braucht Chromium)
#
# Voraussetzung (Zugangsdaten NUR über die Umgebung, nie als Argument):
#   export FRITZ_USER="dein-box-benutzer"     # Benutzer mit Recht "FRITZ!Box-Einstellungen"
#   export FRITZ_PASSWORD="…"                 # ist es nicht gesetzt, wird verdeckt (getpass) gefragt
#   export FRITZ_URL="http://fritz.box"       # optional, das ist der Default
# Beide Werkzeuge (fritz_lease.py und contrib/fritz_ui.py) lesen diese Variablen selbst —
# deshalb wird hier NICHT ins stdin gepipet (das würde getpass aushebeln und mit leerem
# Passwort erst nach dem Start von Chromium scheitern).
#
# Aufruf:  examples/pin-with-fallback.sh <MAC|IP|Name>   (MAC = stabiler Schlüssel)

set -euo pipefail
cd "$(dirname "$0")/.."
DEV="${1:?Aufruf: examples/pin-with-fallback.sh <MAC|IP|Name>}"

# Exit-Codes von fritz_lease.py: 0 Erfolg · 1 Fehler (Login/Gerät) · 2 geschrieben, aber
# Verifikation widersprach. Nur die 2 rechtfertigt den nächsten Kanal — bei 1 nutzen alle
# drei Kanäle dieselben Zugangsdaten, ein Fallback (samt Browser-Start) wäre sinnlos.

echo "[1/3] REST (api/v0) …"
rc=0; ./fritz_lease.py pin "$DEV" || rc=$?
[[ $rc -eq 0 ]] && exit 0
[[ $rc -eq 1 ]] && { echo "Abbruch: Fehler (Login/Gerät), kein Kanalproblem — Fallback sinnlos."; exit 1; }

echo "[2/3] Verifikation widersprach — Fallback data.lua (browserlos) …"
rc=0; ./fritz_lease.py --via datalua pin "$DEV" || rc=$?
[[ $rc -eq 0 ]] && exit 0
[[ $rc -eq 1 ]] && { echo "Abbruch: Fehler."; exit 1; }

echo "[3/3] data.lua widersprach — letzte Rückfallebene Playwright-UI …"
python3 contrib/fritz_ui.py pin "$DEV"          # liest FRITZ_URL/USER/PASSWORD selbst aus der Umgebung

# Ein Klick ist kein Speichern — unabhängig über REST/query.lua gegenlesen:
echo "→ Verifikation nach UI-Schreibweg:"
./fritz_lease.py verify "$DEV" --expect 1
