> 🤖 **Mit einem LLM „vibe-coded", automatisch von Claude erstellt und veröffentlicht** (Anthropics Claude Code), im Auftrag des Autors. Gegen eine einzelne FRITZ!Box verifiziert; maschinengeschriebener Text, stellenweise holprig.

# PROVENANCE — wie das entstanden ist, und was es nicht ist

**Autor:** Juergen Vejmelka (22236671+jvejmelka@users.noreply.github.com)

## Reverse-engineered, nicht dokumentiert

AVM dokumentiert TR-064 und das AHA-HTTP-Interface. Keines davon deckt feste
DHCP-Leases ab. Alles in diesem Repository über `/api/v0/generic/...`, `data.lua`
und `query.lua` wurde gewonnen durch:

- Endpunkte gegen eine physische FRITZ!Box abklopfen und die Fehlerantworten lesen
  (`bad path` vs. `bad value` ist ein erstaunlich gutes Orakel),
- beobachten, was die box-eigene Weboberfläche sendet,
- den entstandenen Zustand über einen unabhängigen Kanal zurücklesen, um zu
  bestätigen, was tatsächlich gespeichert wurde.

Keine Firmware wurde extrahiert, verändert oder weitergegeben. Kein Code wurde vom
Gerät genommen. Die Schnittstellen sind über das LAN mit normalen
Benutzer-Zugangsdaten erreichbar, auf Hardware im Besitz des Autors.

`api/v0` ist von AVM selbst als `v0` versioniert. Behandle jeden Pfad hier als
Beobachtung über *eine* Firmware-Version, nicht als API-Zusage. Er kann ohne
Vorwarnung brechen und ist von keinem Support abgedeckt.

## Wie es geschrieben wurde

Iterativ, im Dialog mit einem LLM (Claude), gegen ein laufendes Gerät:
Hypothese → Probe → Fehler lesen → nachjustieren. „Vibe-coded", wenn man so will —
mit der wichtigen Einschränkung, dass das Modell diese Endpunkte **nicht** kannte
und nicht kennen konnte: sie sind undokumentiert und in dieser Form in keinem
Trainingskorpus. Jede Aussage in der README trägt, weil sie ausgeführt und
gegengelesen wurde, nicht weil sie richtig klang.

Der Fehlermodus, gegen den das absichert, ist es wert benannt zu werden, weil er
während der Entwicklung wiederholt auftrat: eine selbstsichere, flüssige, falsche
Erklärung. `isTrusted`-Event-Semantik, `content-visibility`, SPA-View-Stack-Kollaps,
Headless-Rendering-Unterschiede — alle plausibel, alle falsch. Die tatsächliche
Ursache war ein nicht angeklickter Reiter, sichtbar auf dem ersten Screenshot, den
niemand angesehen hatte.

## Herangezogene Quellen

Diese haben die Suche geleitet. Feldnamen und Endpunkt-Formen sind Fakten über das
Gerät, keine schöpferische Leistung, und wurden in jedem Fall vor der Verwendung
erneut an der Hardware überprüft. **Aus keiner davon wurde Quellcode kopiert.**

| Quelle | Was sie beitrug |
|---|---|
| [AVM — Schnittstellen (TR-064 / AHA-HTTP)](https://avm.de/service/schnittstellen/) | stellte fest, was TR-064 *nicht* kann |
| [Gist von **Garfonso**, „Manipulate FritzBox 6490 hosts lists using data.lua" (2020)](https://gist.github.com/Garfonso/9b5bbc0ade86ad82185edf3208c72017) | Existenz und grobe Form der Legacy-`edit_device`-Formularfelder — **ohne Lizenzangabe, also nichts kopiert** |
| [administrator.de — „DHCP-Umzug auf Fritz!Box" (2025)](https://administrator.de/forum/dhcp-server-fritzbox-netzwerk-umzug-675349.html) | erster Hinweis, dass `/api/v0/generic/landevice/landevice` existiert und einen `AVM-SID`-Header nimmt |
| [jens-maus/hm_pdetect, Issue #4](https://github.com/jens-maus/hm_pdetect/issues/4) (2015) | die `query.lua`-Syntax `landevice:settings/landevice/list(...)` |
| [kbr/fritzconnection](https://github.com/kbr/fritzconnection) | bestätigte, dass TR-064 keine Aktion für feste Leases hat |

Die Update-Route `/api/v0/generic/landevice/landevice/<UID>` auf FRITZ!OS 8.x fand
sich in keiner davon und scheint öffentlich undokumentiert. Das ist der Hauptgrund,
warum dieses Repository existiert.

## Lizenzhygiene

- Aller Code in diesem Repository wurde dafür geschrieben. Nichts ist eine Kopie
  oder Ableitung der obigen Quellen.
- Wo die Lizenz einer Quelle unklar ist (Forenbeiträge, Gists ohne Lizenzdatei),
  **gilt: alle Rechte vorbehalten, nichts kopieren.** Ein Faktum zu nutzen — dass
  ein Formularfeld `static_dhcp` heißt, dass ein Pfad drei Segmente hat — ist kein
  Kopieren; einen fremden Funktionsrumpf zu übernehmen schon.
- Wer dieses Projekt erweitert, hält diese Linie: aus Beobachtung neu
  implementieren und die Idee zitieren.
- Marken: FRITZ!Box, FRITZ!OS und AVM sind Marken der AVM GmbH. Dieses Projekt
  steht in keiner Verbindung zu AVM, wird von AVM nicht unterstützt oder gebilligt.
- Dieses Repository steht unter **CC0 1.0** — gemeinfrei. Das deckt nur diesen
  Code. Die Freigabe eigener Arbeit gibt keine Rechte an fremder: die obigen
  Quellen bleiben unter den Bedingungen ihrer Autoren (oft keine genannt, was
  „alle Rechte vorbehalten" bedeutet).

## Die Befunde reproduzieren

Alles in den Tabellen der README lässt sich in etwa einer Stunde an jeder eigenen
FRITZ!Box nachvollziehen:

1. Benutzer mit der Berechtigung *FRITZ!Box-Einstellungen* anlegen.
2. Login via `login_sid.lua?version=2` (PBKDF2 Challenge-Response).
3. `GET /query.lua?...list(name,ip,mac,UID,static_dhcp)` — Ausgangslage.
4. Schreibpfade abklopfen, Status **und** Body je Versuch notieren. Der Unterschied
   zwischen `bad path` und `bad value` sagt, ob eine Route existiert.
5. Nach jedem Schreiben aus einem anderen Kanal zurücklesen.

Verhält sich dein Modell oder deine Firmware anders, ist das meldenswert — die
Tabelle pro Modell ist der Teil dieses Projekts mit bleibendem Wert.
