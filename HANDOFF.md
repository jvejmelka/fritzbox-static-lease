> 🤖 **Mit einem LLM „vibe-coded“, automatisch von Claude erstellt und veröffentlicht** (Anthropics Claude Code), im Auftrag des Autors. Gegen eine einzelne FRITZ!Box verifiziert; maschinengeschriebener Text, stellenweise holprig. Hintergrund: [PROVENANCE.md](PROVENANCE.md).

# Start prompt for Claude Code

Copy this into Claude Code in the repo directory. It is written to be pasted
as-is.

---

Lies zuerst `CLAUDE.md` und `PROVENANCE.md`, dann `README.md`.

Kontext: Das Repo enthält eine **neu geschriebene, nicht gegen Hardware
getestete** Fassung des Tools. Die produktive, getestete Fassung liegt bei mir
lokal unter `/root/homelab/fritz-lease.py` (plus `fritz-ui.py` für den
Playwright-Weg). Die Befunde im README stammen aus echten Läufen gegen eine
FRITZ!Box 7520 mit FRITZ!OS 8.25 (Build 175.08.25), Stand 2026-09-07, und sind belastbar; der Code im Repo ist
es noch nicht.

Aufgaben, in dieser Reihenfolge:

1. **Abgleich.** Vergleiche `fritz_lease.py` im Repo mit meiner getesteten
   Fassung. Wo sie abweichen, gewinnt die getestete — besonders bei Login,
   `query.lua`-Auswertung und der Struktur der REST-GET-Antwort. In
   `verify()` steht aktuell eine Regex über das JSON, weil das echte
   Antwortformat beim Schreiben des Repos nicht vorlag; ersetz das durch
   einen direkten Feldzugriff, sobald du die echte Struktur siehst.

2. **Erster Lauf.** `list`, `find`, `verify` gegen die Box — nur lesend.
   Danach `pin` auf ein bereits gepinntes Gerät (muss idempotent „nichts zu
   tun" melden, Exit 0).

3. **Selektoren prüfen** in `contrib/fritz_ui.py`. Der Login-Teil ist
   geraten. Alles ab „Tab Heimnetz klicken" entspricht dem, was bei mir
   funktioniert hat.

4. **Offene Punkte abarbeiten** (in `CLAUDE.md` unter „Open / untested"),
   jeweils mit echtem Lauf und Gegenlesen, und danach die Tabellen in README
   und CLAUDE.md aktualisieren.

Regeln, die hier gelten (stehen ausführlich in `CLAUDE.md`):

- Kein ✅ ohne einen echten Lauf gegen die Box. „Der Codepfad existiert" zählt
  nicht. Wenn etwas ungetestet ist, schreib ⬜ und sag es.
- HTTP 200 ist kein Beweis. Nach jedem Schreibvorgang aus einem anderen Kanal
  gegenlesen.
- Bei allem, was die Weboberfläche betrifft: erst Screenshot ansehen, dann DOM
  vermessen.
- Schemata nicht erfinden: GET holen, ein Feld ändern, zurückschicken.
- Nichts aus fremden Quellen kopieren. Feldnamen und Pfade sind Fakten über
  das Gerät und dürfen benutzt werden; fremde Funktionsrümpfe nicht. Wenn du
  während der Arbeit auf eine Vorlage stößt, notier sie in `PROVENANCE.md`
  unter „Sources consulted", statt Code zu übernehmen.
- **Keine echten Daten ins Repo.** Keine MACs, IPs, UIDs, Benutzernamen,
  Hostnamen, Passwörter — auch nicht in Beispielen, Kommentaren oder
  Commit-Messages. Beispiele nutzen `192.168.178.x` und
  `AA:BB:CC:DD:EE:FF`. Zugangsdaten kommen ausschließlich aus
  `FRITZ_USER` / `FRITZ_PASSWORD` / stdin; ein `--password`-Flag wird nicht
  wieder eingebaut.
- Vor dem ersten Push einmal `git grep -nE "192\.168\.2\.|landevice[0-9]"`
  und nach der eigenen MAC-Präfixliste suchen. Was einmal gepusht ist, steht
  dauerhaft in der Git-History, auch nach einem späteren Commit.

Wenn dir etwas widersprüchlich vorkommt, frag nach, statt zu raten. Genau das
Raten hat bei diesem Projekt die meiste Zeit gekostet.
