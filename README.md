> 🤖 **Mit einem LLM „vibe-coded", dann automatisch von Claude erstellt und veröffentlicht** (Anthropics Claude Code), im Auftrag des Autors. Reverse-engineered gegen eine einzelne FRITZ!Box — jeder Befund wurde ausgeführt und gegengelesen, aber der Text ist maschinengeschrieben und liest sich stellenweise holprig. Hintergrund: [PROVENANCE.md](PROVENANCE.md).

# fritzbox-static-lease

*English summary for search: set static DHCP leases ("always assign the same IPv4 address") on an AVM FRITZ!Box from a script, and verify they stuck. TR-064 / `fritzconnection` cannot do this; this uses the undocumented internal `api/v0` REST route. Keywords: FRITZ!Box static DHCP lease, feste IP zuweisen, api/v0, query.lua, FRITZ!OS 8.x.*

---

Feste DHCP-Leases („diesem Netzwerkgerät immer die gleiche IPv4-Adresse zuweisen")
auf einer AVM FRITZ!Box per Skript setzen — und **verifizieren**, dass die Box sie
wirklich gespeichert hat.

**TR-064 kann das nicht.** `fritzconnection` und jedes andere TR-064-Werkzeug liest
die Geräteliste, aber setzt das Lease-Flag nicht, weil keine TR-064-Aktion es
freigibt. Dieses Skript nutzt stattdessen die box-eigenen internen Schnittstellen.

**Getestet auf:** FRITZ!Box 7520 (1&1), FRITZ!OS **8.25** (Build-String `175.08.25`
— eine Firmware-Version, *kein* Datum). **Zuletzt verifiziert: 2026-09-07.** Die
REST-API ist undokumentiert und von AVM selbst als `v0` versioniert — jeder Pfad
hier ist firmware-spezifisch.

## Kanäle

Das Flag über *einen* Kanal schreiben, über einen *anderen* zurücklesen.

| Kanal | schreiben | lesen / prüfen | Anmerkung |
|---|---|---|---|
| REST `api/v0` | ja | ja | primär; eine Anfrage, kein Browser |
| `data.lua` | ja | — | Legacy-Formular-POST, auf FRITZ!OS 8.25 noch akzeptiert |
| `query.lua` | — | ja | unabhängig vom REST-Stack; die billige Gegenprobe |
| Web-UI (Playwright) | ja | ja | letzte Rückfallebene, siehe `contrib/` |
| TR-064 | **nein** | **nein** | keine Aktion, kein Feld |

Drei Schreibkanäle, drei unabhängige Leser. Jeder wurde Ende-zu-Ende gegen ein
bekannt-gepinntes und ein bekannt-ungepinntes Gerät getestet.

## Die REST-Route

```
PUT /api/v0/generic/landevice/landevice/<UID>
Header: AUTHORIZATION: AVM-SID <sid>
Body:   {"static_dhcp": "1"}
-> 200 {}
```

Pfadform: `/api/v0/generic/<modul>/<collection>/<node>`. Das doppelte
`landevice/landevice` ist kein Tippfehler: das erste Segment ist das Modul, das
zweite die Collection.

## Was NICHT geht (damit du es nicht wiederholst)

| Versuch | Ergebnis |
|---|---|
| `PUT /api/v0/generic/landevice/<UID>` | `400 {"message":"bad path","code":3002}` |
| `PUT /api/v0/generic/landevice/landevice` | `400 bad path` |
| `POST /api/v0/generic/landevice/landevice` für ein **bestehendes** Gerät | `400 transaction fail` + `bad value` auf Feld `UID` |
| TR-064 `Hosts`-Dienst | liefert MAC/IP/Name/aktiv, aber kein Feld für die feste Zuweisung |
| HTTP 200 als Erfolgsnachweis | die Box liefert 200 auch für verworfene Schreibvorgänge; immer gegenlesen |

## Installation

```bash
git clone https://github.com/jvejmelka/fritzbox-static-lease
cd fritzbox-static-lease
pip install requests
```

Lege einen eigenen FRITZ!Box-Benutzer mit der Berechtigung *FRITZ!Box-Einstellungen*
an — kein Admin-Konto in Skripten. Hat das Konto die „Zusatzbestätigung"
(per Telefon/Taste) aktiv, scheitern Schreibvorgänge stillschweigend; für diesen
Benutzer abschalten.

Zugangsdaten kommen aus den Umgebungsvariablen `FRITZ_URL` / `FRITZ_USER` /
`FRITZ_PASSWORD`, aus stdin oder — interaktiv — aus einer verdeckten
`getpass`-Abfrage. **Kein `--password`-Flag:** Kommandozeilen-Argumente stehen in
der Prozessliste und landen in der Shell-History.

## Benutzung

```bash
export FRITZ_USER="dein-box-benutzer"      # FRITZ_URL default: http://fritz.box
# Passwort: export FRITZ_PASSWORD=…, per stdin, oder interaktiv verdeckt abgefragt

# alle bekannten Geräte mit ihrem aktuellen Flag
./fritz_lease.py list

# Gerät festnageln — die MAC ist der stabile Schlüssel (UIDs ändern sich beim Reset)
./fritz_lease.py pin AA:BB:CC:DD:EE:FF

# derselbe Vorgang über den browserlosen Fallback
./fritz_lease.py --via datalua pin AA:BB:CC:DD:EE:FF

# nur prüfen, ohne zu schreiben
./fritz_lease.py verify 192.168.178.50 --expect 1

# Massenbetrieb: eine MAC oder IP pro Zeile, # für Kommentare
./fritz_lease.py batch leases.txt
```

Exit-Codes: `0` Erfolg (oder schon korrekt), `1` Fehler, `2` geschrieben, aber
Verifikation widerspricht.

`pin` ist idempotent — ist das Flag schon gesetzt, meldet es das und gibt `0`
zurück; sicher in Cron oder Ansible.

## Verifikation

Jeder Schreibvorgang wird aus einem *anderen* Kanal zurückgelesen als dem, mit dem
geschrieben wurde, und die Leser müssen übereinstimmen. `verify()` fragt die
REST-API **und** `query.lua`; widersprechen sie sich, oder stimmt der Wert nicht,
endet der Befehl mit ≠ 0.

Das ist wichtiger, als es klingt: `data.lua` liefert HTTP 200 auch für
Formular-POSTs, die es nicht übernimmt, und die REST-API liefert `200 {}`
unabhängig vom Ergebnis. **Kein Statuscode ist ein Beweis.**

## Der Weg über die Weboberfläche (Plan C)

Auf FRITZ!OS 8.x ist die Oberfläche eine SPA („js3"). Die eine Falle: die Checkbox
**„IPv4-Adresse dauerhaft zuweisen" liegt nicht auf dem Tab „Allgemein"**, sondern
auf **„Heimnetz"** der Geräte-Detailseite. Auf dem inaktiven Tab ist sie im DOM
vorhanden, aber ohne Layout (`getBoundingClientRect()` = 0×0), obwohl `display:block`
und `visibility:visible` — kein `display:none`, kein `hidden`, kein
`content-visibility`. Das sieht aus wie ein Renderfehler und ist keiner. Also erst
den Tab klicken. **Headless funktioniert danach** einwandfrei; ein virtuelles
Display (xvfb) ist nicht nötig. Details in `contrib/fritz_ui.py`.

Methodische Lehre: bei UI-Automatisierung zuerst einen **Screenshot** ansehen, dann
das DOM vermessen. Die Ursache oben (ein nicht angeklickter Reiter) war auf dem
ersten Bild sofort zu sehen; über DOM-Analyse allein kostet sie Stunden, weil sich
für „Element ohne Layout-Box" ein halbes Dutzend plausibler, falscher Erklärungen
anbietet.

## Stabile Schlüssel & IP ändern

UIDs (`landeviceNNNN`) sind **nicht** stabil — sie ändern sich beim
„Netzwerkverbindung zurücksetzen" eines Geräts und können sich bei
Firmware-Updates verschieben. Deshalb ist die **MAC** der Schlüssel, und das Skript
löst die UID zur Laufzeit auf. `{"static_dhcp":"1"}` hält die IP fest, die das Gerät
*gerade* hat; für eine *andere* Adresse muss `ip` in den Body (`--ip`, auf
FRITZ!OS 8.25 nicht durchgetestet).

## Beiträge

Befunde von anderen Modellen und Firmwareversionen sind willkommen: Modell,
FRITZ!OS-Version, welche Route ging und welche nicht — genau diese Tabelle fehlt im
Netz. Arbeitsregeln stehen in [CLAUDE.md](CLAUDE.md) (gelten für Menschen genauso):
kein ✅ ohne Lauf, HTTP 200 ist kein Beweis, Screenshot vor DOM-Analyse, Schemata
spiegeln statt raten, MAC statt UID. Beiträge unter derselben Freigabe (CC0); kein
Code mit restriktiverer Lizenz.

FRITZ!Box, FRITZ!OS und AVM sind Marken der AVM GmbH. Dieses Projekt steht in keiner
Verbindung zu AVM.

## Lizenz

**CC0 1.0** — gemeinfrei, siehe [LICENSE](LICENSE). Nutzen, ändern, weitergeben,
kommerziell verwerten: alles erlaubt, ohne Namensnennung, ohne Rückfrage. Die
Freigabe gilt für den Code dieses Repositorys, nicht für Marken Dritter.

**Autor:** Juergen Vejmelka (22236671+jvejmelka@users.noreply.github.com)
