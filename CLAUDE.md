> 🤖 **Mit einem LLM „vibe-coded", automatisch von Claude erstellt und veröffentlicht** (Anthropics Claude Code), im Auftrag des Autors. Gegen eine einzelne FRITZ!Box verifiziert; maschinengeschriebener Text, stellenweise holprig. Hintergrund: [PROVENANCE.md](PROVENANCE.md).

# CLAUDE.md — Projektkontext

Zuerst lesen. Diese Datei sagt, was bewiesen ist, was geraten ist und nach welchen
Regeln dieses Projekt arbeitet. Sie gilt für Menschen wie für KI-Agenten.

## Worum es geht

Ein CLI-Werkzeug, um feste DHCP-Leases („IPv4-Adresse dauerhaft zuweisen") auf einer
AVM FRITZ!Box zu setzen und zu **verifizieren**. TR-064 kann das nicht, also spricht
das Werkzeug die box-eigenen, undokumentierten internen Schnittstellen an.

Alles hier wurde **reverse-engineered** — gegen ein physisches Gerät, durch
Beobachten des HTTP-Verkehrs und Abklopfen von Endpunkten. Nichts stützt sich auf
Hersteller-Doku, weil es für diese Endpunkte keine gibt. Siehe PROVENANCE.md.

## Harte Regeln für dieses Projekt

1. **Kein ✅ ohne echten Lauf.** Eine Fähigkeit gilt erst als „unterstützt", wenn
   sie gegen eine echte Box ausgeführt und das Ergebnis zurückgelesen wurde. „Der
   Codepfad existiert" ist kein Beweis. Diese Regel hat in der Entwicklung schon
   zwei Fehlannahmen gefangen.
2. **HTTP 200 beweist nichts.** Die Box liefert 200 auch für Schreibvorgänge, die
   sie still verwirft. Jeder Schreibvorgang wird durch Zurücklesen geprüft —
   idealerweise über einen *anderen* Kanal als den, mit dem geschrieben wurde.
3. **Screenshot vor DOM.** Bei allem, was die Web-UI berührt: erst ein Bild ansehen,
   dann das DOM vermessen. Sechs Runden `getBoundingClientRect`-Forensik wurden
   einmal durch einen Screenshot gelöst, der einen nicht angeklickten Reiter zeigte.
4. **Schemata nicht raten — spiegeln.** Objekt per GET holen, *ein* Feld ändern,
   per PUT zurückschreiben. Erfundene Body-Formen erzeugten stundenlang `bad value`
   / `bad path`.
5. **Die MAC ist der Schlüssel, nicht die UID.** UIDs (`landeviceNNNN`) ändern sich
   beim Geräte-Reset und können sich über Firmware-Updates verschieben.

## Stand des Codes

| Datei | Status |
|---|---|
| `fritz_lease.py` | **Kern gegen echte Box getestet (2026-09-07):** `list`, `verify`, `pin`/`unpin` via REST, Gegenlesen via REST **und** `query.lua`. **Nicht** in dieser Form gelaufen: `--via datalua`, `batch`, `--ip` — diese ⬜. |
| `contrib/fritz_ui.py` | **Nicht in dieser Form gegen Hardware gelaufen.** Selektoren rekonstruiert; die *Technik* (erst Tab „Heimnetz", dann sichtbaren Übernehmen-Button treffen, headless) ist an der Box verifiziert. |
| `README.md` | Befunde stammen aus echten Läufen und sind belastbar. |

## Gegen Hardware verifiziert (FRITZ!Box 7520, FRITZ!OS 8.25 = Build 175.08.25, 2026-09-07)

- `PUT /api/v0/generic/landevice/landevice/<UID>` mit `{"static_dhcp":"1"}` → 200, persistiert
- `POST /data.lua` Legacy-`edit_device`-Formular → schreibt auf FRITZ!OS 8.25 erfolgreich
- `GET /query.lua` `landevice:settings/landevice/list(...,static_dhcp)` → liest das Flag
- Web-UI via Playwright, **headless**: Liste → Gerät → **Tab „Heimnetz"** → Checkbox → Übernehmen
- Playwright kalter Leseabruf (`aria-checked`) gegen ein gepinntes und ein ungepinntes Gerät

## Bekannt-schlecht (nicht erneut versuchen, steht in der README)

- `PUT /api/v0/generic/landevice/<UID>` → `bad path`
- `POST .../landevice/landevice` für ein bestehendes Gerät → `transaction fail`, `bad value` auf `UID`
- TR-064 für das Flag — das Feld existiert in keiner Aktion
- xvfb / headed-Modus als Fix für die 0×0-Checkbox — die Ursache war der Reiter

## Offen / ungetestet

- `--ip` (ein Gerät auf eine *andere* Adresse setzen, nicht nur die aktuelle
  festhalten). Body braucht `ip`; bei belegter Ziel-IP (auch durch einen inaktiven
  Eintrag) ist ein Konflikt zu erwarten.
- `unpin` via `--via datalua` (Weglassen des Schlüssels) — nur die „on"-Richtung
  wurde getestet.
- `--via datalua` mit dem hartkodierten `kisi_profile`-Fallback — kann bei einem
  Gerät mit anderem Zugangsprofil dessen Profil ändern; vor Nutzung das aktuelle
  Profil einlesen.
- Jedes andere Modell als die 7520, jede andere Firmware als 8.25 (Build 175.08.25).

Diese in der Doku als ⬜ führen, bis sie jemand ausführt. Nicht allein aufgrund von
Code-Lesen auf ✅ heben.

## Konventionen

- Python 3.10+, nur `requests`. Playwright bleibt optional und in `contrib/`.
- Exit-Codes: 0 = Erfolg oder schon korrekt, 1 = Fehler, 2 = geschrieben, aber
  Verifikation widerspricht.
- Zugangsdaten: `FRITZ_URL` / `FRITZ_USER` / `FRITZ_PASSWORD`, stdin oder eine
  interaktive verdeckte Abfrage. Nie ein `--password`-Flag, nie ein Default-Benutzer
  im Beispiel, nie ein Zugangsdatum in einer committeten Datei. Neue Features mit
  Auth folgen demselben Muster.
- **Nichts, was das Netz des Autors identifiziert, kommt ins Repo:** keine echten
  MACs, IPs, UIDs, Benutzer- oder Hostnamen. Beispiele nutzen Doku-Bereiche
  (`192.168.178.x`) und Platzhalter-MACs (`AA:BB:CC:DD:EE:FF`). **Vor jedem Push
  `git grep` über echte Werte laufen lassen — die Git-History vergisst nichts,
  ein späterer Commit entfernt nichts, was einmal gepusht wurde.**
- Lizenz: CC0 1.0 (gemeinfrei). Beiträge werden zu denselben Bedingungen
  angenommen; kein Code mit restriktiverer Lizenz wird hereingemergt.
- Die Befundtabelle in der README aktuell halten — sie ist hier das eigentliche
  Produkt. Der Code veraltet mit der nächsten Firmware; die Tabelle sagt der
  nächsten Person, wo sie anfängt.
- Sprache: alle Markdown-Dateien auf Deutsch (Zielgruppe ist die deutsche
  FRITZ!Box-Community), Code und Kommentare auf Englisch. `LICENSE` ist der
  kanonische CC0-Text und wird nicht angefasst (sonst bricht die Lizenz-Erkennung).

## Wie das gebaut wurde

Iterativ, im Dialog mit einem LLM, gegen ein laufendes Gerät — „vibe-coded" im
wörtlichen Sinn: Hypothese, Probe, Fehler lesen, nachjustieren. Das trug, weil jeder
Schritt mit einer Verifikation an der Box endete, nicht weil das Modell die API
kannte. Es kannte sie nicht; niemand tut das. Diese Schleife beibehalten, wer das
erweitert.
