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

# Bewusst die explizite if-Form, nicht `[[ … ]] && exit`: letzteres funktioniert unter
# set -e nur dank der &&-Listen-Ausnahme und wird zur stillen Abbruchfalle, sobald jemand
# so eine Zeile ans Ende einer Funktion/Datei verschiebt. Ein Beispiel sollte das nicht vorführen.

echo "[1/3] REST (api/v0) …"
rc=0; ./fritz_lease.py pin "$DEV" || rc=$?
if [[ $rc -eq 0 ]]; then exit 0; fi
if [[ $rc -eq 1 ]]; then echo "Abbruch: Fehler (Login/Gerät), kein Kanalproblem — Fallback sinnlos."; exit 1; fi

echo "[2/3] Verifikation widersprach (Exit 2) — Fallback data.lua (browserlos) …"
rc=0; ./fritz_lease.py --via datalua pin "$DEV" || rc=$?
if [[ $rc -eq 0 ]]; then exit 0; fi
if [[ $rc -eq 1 ]]; then echo "Abbruch: Fehler."; exit 1; fi

echo "[3/3] data.lua widersprach (Exit 2) — letzte Rückfallebene Playwright-UI …"
# Kein Exit-Code-Abfang hier, und das ist Absicht: schlägt fritz_ui.py fehl, bricht set -e
# das Skript ab und die Verifikation unten läuft bewusst nicht mehr — der UI-Weg war die
# letzte Option, es gäbe keinen weiteren Kanal.
python3 contrib/fritz_ui.py pin "$DEV"          # liest FRITZ_URL/USER/PASSWORD selbst aus der Umgebung

# Ein Klick ist kein Speichern — unabhängig über REST/query.lua gegenlesen:
echo "→ Verifikation nach UI-Schreibweg:"
./fritz_lease.py verify "$DEV" --expect 1
