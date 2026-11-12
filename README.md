# Trainingsblick

Ein Programm für Windows, das deine Strava-Aktivitäten übersichtlich auswertet und schöne Bilder und Videos zum Teilen macht.
Es läuft auch auf dem Mac: siehe [Trainingsblick auf dem Mac](#trainingsblick-auf-dem-mac).

### [⬇ Trainingsblick für Windows herunterladen](https://github.com/tp-codings/trainingsblick/releases/latest)

Auf der Seite unten bei „Assets“ die Datei `Trainingsblick-Setup-….exe` anklicken. Anleitung: [Installation](#installation).
Fragen oder Probleme: per Nachricht auf Instagram an [@tritopa](https://www.instagram.com/tritopa/).

- **Übersicht**: wie fit du gerade bist, deine Woche, dein nächster Wettkampf, die letzten Einheiten
- **Aktivitäten**: Woche, Monat oder Jahr mit Zahlen, Kalender und allen Einheiten
- **Körperdaten** (optional, mit Garmin): Schlaf, HRV, Ruhepuls, Body Battery, VO2max
- **Zeiten**: Bestzeiten, Rekorde und wie du dich entwickelst
- **Karte**: alle deine Strecken auf einer Karte
- **Share Studio**: Bild einer Einheit, Sammelbild einer ganzen Woche oder ein Video, in dem die Strecken nacheinander erscheinen (mit Sound)

Alles läuft auf deinem eigenen PC. Deine Daten gehen an niemanden außer Strava (und Garmin, wenn du das verbindest).

---

## Was du brauchst

- Einen PC mit **Windows 10 oder 11**
- Ein **Strava-Konto**
- Optional: ein **Garmin-Konto** (für die Körperdaten)
- Etwa **10 Minuten** für die Einrichtung

Sonst musst du nichts installieren: Das Programm bringt alles mit.

---

## Installation

### Schritt 1: Installieren

1. Öffne <https://github.com/tp-codings/trainingsblick/releases/latest>
2. Klicke unten bei „Assets“ auf **`Trainingsblick-Setup-….exe`**, die Datei landet in deinem Ordner **Downloads**
3. Doppelklicke die Datei
4. Falls Windows warnt („Der Computer wurde durch Windows geschützt“): auf **„Weitere Informationen“** klicken, dann auf
   **„Trotzdem ausführen“**. Das kommt, weil das Programm neu und nicht bei Microsoft registriert ist.
5. Im Installer auf **„Installieren“** und am Ende auf **„Fertigstellen“** klicken. Adminrechte brauchst du nicht.

Trainingsblick öffnet sich in einem eigenen Fenster mit der **Einrichtung**. Später startest du es über das Startmenü
oder die Verknüpfung **„Trainingsblick“** auf dem Desktop.

### Schritt 2: Mit Strava verbinden

Strava erlaubt Programmen nur Zugriff, wenn du dafür eine eigene, kostenlose „API-App“ anlegst. Das klingt technischer, als es ist,
und die Einrichtung in Trainingsblick führt dich mit Kopier-Knöpfen durch jeden Schritt:

1. In der Einrichtung auf **„Strava öffnen“** klicken (oder <https://www.strava.com/settings/api> öffnen) und bei Strava anmelden
2. Fülle das Formular so aus:

   | Feld | Was du einträgst |
   |---|---|
   | Application Name | `Mein Dashboard` (beliebig) |
   | Category | `Data Importer` (oder etwas anderes) |
   | Club | leer lassen |
   | Website | `http://localhost` |
   | Application Description | leer lassen oder irgendwas |
   | **Authorization Callback Domain** | **`localhost`** (genau so, ohne http und ohne Schrägstrich) |

3. Bestätige die Bedingungen und klicke auf **„Create“**.
   Falls Strava nach einem Bild für die App fragt: In der Einrichtung auf **„passendes Bild speichern …“** klicken und dieses Bild hochladen.
4. Du siehst jetzt deine App mit **Client ID** (eine Zahl) und **Client Secret** (auf **„Show“** klicken, eine lange Buchstaben-Zahlen-Folge)
5. Kopiere beide in die Einrichtung von Trainingsblick und klicke auf **„Mit Strava verbinden …“**
6. Im Browser öffnet sich Strava. Lass den Haken bei **„Aktivitätsdaten ansehen“** (bzw. „View data about your activities“) gesetzt und klicke auf **„Autorisieren“**
7. Es erscheint „Mit Strava verbunden ✔“. Diesen Browser-Tab kannst du schließen.

Trainingsblick lädt jetzt deine Aktivitäten. Die neuesten siehst du nach wenigen Sekunden, ältere kommen im Hintergrund dazu.
Bestzeiten, Runden und Wetter füllen sich über die nächsten Stunden bis Tage nach (Strava erlaubt nur eine begrenzte Zahl
an Abrufen pro Viertelstunde und Tag).

> **Wichtig:** Client Secret und Zugangsdaten bleiben verschlüsselt auf deinem PC (siehe „Sicherheit“). Gib sie niemandem weiter.

### Schritt 3: Garmin (optional)

Wenn du eine Garmin-Uhr hast, kannst du Schlaf, HRV, Ruhepuls und mehr anzeigen lassen:

1. In der Einrichtung (oder später unter **Körperdaten**) **E-Mail und Passwort von Garmin Connect** eingeben
2. Wenn Garmin einen **Bestätigungscode** schickt (per E-Mail oder App), diesen eintragen

Das Passwort wird nicht gespeichert, nur ein Zugangs-Schlüssel von Garmin, und der verschlüsselt (siehe „Sicherheit“).
Ohne Garmin fehlt nur der Bereich Körperdaten, alles andere funktioniert.

> **Gut zu wissen:** Garmin bietet für so etwas keinen offiziellen Zugang. Das Programm nutzt das freie Paket
> [garminconnect](https://github.com/cyberjunky/python-garminconnect), das sich wie die Garmin-Connect-Webseite anmeldet.
> Garmin kann das jederzeit ändern (dann geht der Abruf eine Weile nicht, bis es ein Update gibt) oder bei zu vielen
> Anmeldungen kurz sperren. Wer das nicht möchte, lässt Garmin einfach weg.

### Schritt 4: Ziel (optional)

Trainierst du auf einen Wettkampf hin? Trag ihn mit Datum ein, dann zeigt die Übersicht den Countdown.
Ein Wochenziel in Stunden ist auch möglich. Beides lässt sich später unter **Einstellungen …** ändern.

---

## Trainingsblick auf dem Mac

Trainingsblick läuft auch unter **macOS** (getestet mit macOS 27 auf einem Mac mit Apple-Chip), mit denselben Funktionen
wie unter Windows. Es gibt zwei Wege: eine **fertige App** zum Weitergeben, die alles mitbringt (als `.dmg`, muss einmal
selbst gebaut werden), oder der Start **aus dem Quellcode**, der sich beim ersten Mal selbst einrichtet. Alles Weitere in
dieser Anleitung (Strava verbinden, Garmin, Bedienung) gilt genauso.

### Als fertige App (.dmg)

Auf dem Mac, der die App bekommt, muss nichts weiter installiert sein (kein Python, kein Terminal).

**Bauen** (einmal, auf einem Mac mit eingerichtetem Programmordner und den Xcode-Werkzeugen, `xcode-select --install`):

```
.venv/bin/python installer/mac_bauen.py
```

Heraus kommt `installer/build/Trainingsblick-<Version>-mac-arm64.dmg` (rund 35 MB) für Macs mit Apple-Chip. Für einen
Intel-Mac: `--arch x86_64` anhängen (ungetestet). Die App läuft ab macOS 11.

**Installieren:** die `.dmg` öffnen und **Trainingsblick** auf **Programme** ziehen, dann aus dem Programme-Ordner oder dem
Launchpad starten.

- Die App ist nicht bei Apple beglaubigt (dafür bräuchte es ein kostenpflichtiges Entwicklerkonto). Kam die `.dmg` per
  AirDrop, Mail oder Download, meldet macOS beim **ersten** Start deshalb, die App lasse sich nicht überprüfen: Meldung
  mit **„Fertig“** schließen, dann **Systemeinstellungen → Datenschutz & Sicherheit**, ganz unten **„Dennoch öffnen“**.
  Danach startet sie wie jede andere App. (Über einen USB-Stick kopiert kommt die Meldung in der Regel nicht.)
- **Update:** neue `.dmg` bauen und die App in „Programme“ ersetzen. Einstellungen und Daten bleiben erhalten. Danach
  fragt macOS einmal nach dem Schlüsselbund (Anmeldepasswort eingeben, **„Immer erlauben“**).
- **Entfernen:** die App aus „Programme“ in den Papierkorb legen. Die Daten liegen in
  `~/Library/Application Support/Trainingsblick`, die Zugänge als Einträge „Trainingsblick …“ in der Schlüsselbundverwaltung.

### Aus dem Quellcode: installieren und starten

1. Den Programmordner mit dem Quellcode (er muss die Mac-Dateien enthalten, z. B. „Trainingsblick starten.command“)
   dorthin legen, wo er bleiben soll.
2. Im Ordner **„Trainingsblick starten.command“** doppelklicken. Es öffnet sich ein Terminal-Fenster, das einmalig alles
   einrichtet (1-2 Minuten): eine eigene Python-Umgebung im Programmordner, die Zusatzpakete und den Starter
   **„Trainingsblick“** (Trainingsblick.app).
   - Fehlt **Python 3.12 oder neuer**, bietet das Skript an, es mit [Homebrew](https://brew.sh) zu installieren. Ohne
     Homebrew öffnet es die Download-Seite von python.org; danach die Datei noch einmal doppelklicken.
   - Meldet macOS, die Datei stamme von einem „nicht verifizierten Entwickler“ (bei einem aus dem Internet geladenen Ordner):
     **Systemeinstellungen → Datenschutz & Sicherheit**, dort unten auf **„Dennoch öffnen“** klicken.
3. Trainingsblick öffnet sich in einem eigenen Fenster. Künftig genügt ein Doppelklick auf **„Trainingsblick“** im
   Programmordner; die App lässt sich auch ins Dock ziehen. Zum Ausprobieren ohne Strava: **„Demo starten.command“**.

**Nachfragen von macOS beim ersten Start** (jeweils einmal bestätigen):
- *„Trainingsblick“ möchte auf Dateien in deinem Ordner „Schreibtisch“ (bzw. „Dokumente“, „Downloads“) zugreifen*:
  kommt nur, wenn der Programmordner dort liegt. Mit **„Erlauben“** bestätigen, sonst kann das Programm sich selbst nicht lesen.
- *… möchte auf den Schlüsselbund zugreifen*: kann nach einem Update von Python kommen. Anmeldepasswort des Mac eingeben
  und **„Immer erlauben“** wählen.

### Was auf dem Mac anders ist

| Thema | Windows | Mac |
|---|---|---|
| Start | Startmenü / Desktop-Verknüpfung | „Trainingsblick“ (Trainingsblick.app) im Programmordner oder im Dock |
| Fenster | Edge oder Chrome als App-Fenster | eigenes Fenster mit der Technik von Safari (WebKit); fehlt das Paket dafür: Edge/Chrome/Brave als App-Fenster, sonst ein Tab im Standardbrowser |
| Einstellungen und Daten | `%APPDATA%\Trainingsblick` | `~/Library/Application Support/Trainingsblick` (im Finder: **Gehe zu → Gehe zum Ordner …**) |
| Zugangsdaten | DPAPI, `%LOCALAPPDATA%\Trainingsblick\geheim` | Schlüsselbund „Anmeldung“, Einträge „Trainingsblick (strava)“ und „Trainingsblick (garmin)“ |
| Eigene Sounds | `%APPDATA%\Trainingsblick\ton` | `~/Library/Application Support/Trainingsblick/ton` |
| Vorschlag für Bilder und Videos | `Bilder\Trainingsblick` | `Bilder/Trainingsblick` in deinem Benutzerordner |
| Tastatur | Strg+Z, Strg+C … | ⌘Z, ⌘C … |

**Sicherheit:** Die Zugangsdaten (Strava: Client Secret und Tokens, Garmin: Zugangs-Schlüssel) liegen im
macOS-Schlüsselbund, verschlüsselt mit deinem Anmeldepasswort, und nirgends als Datei. Wie unter Windows gilt: Ein anderes
Benutzerkonto oder ein kopierter Ordner können damit nichts anfangen; vor Schadsoftware unter deinem eigenen Konto schützt
das nicht. Ansehen oder löschen kannst du die Einträge im Programm **Schlüsselbundverwaltung** (nach „Trainingsblick“ suchen).

**Update:** Der Hinweis „Neue Version … herunterladen“ öffnet die Release-Seite. Die Setup-Datei dort ist nur für
Windows; für den Mac zählt der neue Quellcode. Enthält er die Mac-Dateien, den alten Programmordner einfach ersetzen
(Trainingsblick vorher beenden) und wieder „Trainingsblick starten.command“ doppelklicken. Sind die Mac-Anpassungen nur
in deinem eigenen Ordner vorhanden (mit `git` geholt und angepasst), die neue Version dazuholen, ohne sie zu verlieren:
im Terminal im Programmordner `git stash`, dann `git pull`, dann `git stash pop`. Einstellungen, Zugänge und geladene
Daten bleiben in jedem Fall erhalten, sie liegen nicht im Programmordner.

**Deinstallieren:** den Programmordner löschen, dazu `~/Library/Application Support/Trainingsblick` und in der
Schlüsselbundverwaltung die Einträge „Trainingsblick“.

| Problem auf dem Mac | Lösung |
|---|---|
| „Trainingsblick“ öffnet sich nicht (Symbol hüpft kurz im Dock) | **Systemeinstellungen → Datenschutz & Sicherheit → Dateien & Ordner**: bei „Trainingsblick“ den Zugriff auf den Ordner erlauben, in dem das Programm liegt. Oder den Programmordner aus „Schreibtisch“/„Dokumente“ heraus verschieben und „Trainingsblick starten.command“ erneut doppelklicken. |
| Nach dem Verschieben des Programmordners startet nichts mehr | „Trainingsblick starten.command“ im Ordner doppelklicken (bei Bedarf vorher den Ordner `.venv` und Trainingsblick.app löschen, dann wird neu eingerichtet). |
| Nach einem großen Python-Update (z. B. 3.13 → 3.14) startet nichts mehr | Im Programmordner `.venv` und Trainingsblick.app löschen und „Trainingsblick starten.command“ doppelklicken. |
| Strava-Zugang „ließ sich nicht verschlüsselt speichern“ | Die Nachfrage zum Schlüsselbund wurde abgelehnt. Noch einmal verbinden und „Immer erlauben“ wählen. |
| Das Fenster ist weg, das Programm läuft aber noch | Im Dock per Rechtsklick auf „Trainingsblick“ **Beenden** (oder in der Aktivitätsanzeige). |

---

## Bedienung in Kürze

- Links wählst du den Bereich. Unten links: **Aktualisieren** (neue Einheiten holen), **Einstellungen …**, **Einrichtung …**
- Klick auf eine Einheit öffnet die Details. Dort **„Teilen …“** für ein Bild dieser Einheit, **„Studio …“** für mehr Möglichkeiten
- In **Aktivitäten** oben **„Woche/Monat/Jahr teilen …“**: Sammelbild oder Video aus allen Einheiten des Zeitraums
- Im Studio kannst du Werte und die Route im Bild **mit der Maus verschieben**. Rückgängig mit dem Pfeil oben oder Strg+Z.
  „Als Standard“ merkt sich dein Design für das nächste Mal.
- Videos werden als normale MP4-Datei gespeichert (1080 Pixel breit, 30 Bilder pro Sekunde) und lassen sich direkt in
  Instagram, WhatsApp oder Schnittprogramme wie DaVinci Resolve laden.

- Bilder und Videos speicherst du über den normalen Windows-Dialog, wohin du willst. Beim Video kommt nach dem Erstellen
  der Knopf **„Speichern …“**.

---

## Update auf eine neue Version

Gibt es eine neue Version, zeigt Trainingsblick links unten **„Neue Version … herunterladen“**.

1. Darauf klicken: Die Download-Seite öffnet sich
2. Die neue `Trainingsblick-Setup-….exe` herunterladen und doppelklicken (Trainingsblick vorher schließen)

Deine Einstellungen, der Strava-Zugang und die geladenen Daten bleiben dabei erhalten, denn sie liegen nicht im Programmordner (siehe unten).

---

## Wo liegen meine Daten?

Einstellungen und geladene Daten liegen in **`%APPDATA%\Trainingsblick`**
(im Explorer oben in die Adresszeile `%APPDATA%\Trainingsblick` eintippen und Enter drücken):

| Ordner | Inhalt |
|---|---|
| `config\trainingsblick.json` | Einstellungen (Puls, Ziele, Designs, Fenstergröße), nichts Geheimes |
| `cache\` | geladene Aktivitäten, Bestzeiten, Runden, Wetter, Garmin-Daten. Darf gelöscht werden, wird dann neu geladen. |
| `logs\` | Fehlerberichte, falls das Programm abstürzt |
| `ton\` | eigene Sounds für die Videos (optional, siehe unten) |

Die **Zugangsdaten** (Strava und Garmin) liegen getrennt davon verschlüsselt in **`%LOCALAPPDATA%\Trainingsblick\geheim`**.

Bilder und Videos speicherst du, wohin du willst (Vorschlag: `Bilder\Trainingsblick`).

---

## Sicherheit

- **Passwörter** (Strava, Garmin) gibt das Programm nie ein und speichert sie nie. Bei Strava meldest du dich im Browser auf
  strava.com an, bei Garmin geht das Passwort nur einmal direkt an Garmin.
- **Zugangsdaten** (Strava: Client Secret und Tokens, Garmin: Zugangs-Schlüssel) werden mit der Windows-Verschlüsselung
  **DPAPI** gespeichert, demselben Verfahren, mit dem Edge und Chrome deine Passwörter schützen. Die Dateien lassen sich nur
  unter deinem Windows-Konto auf diesem PC öffnen. Ein Backup, ein kopierter Ordner oder ein anderes Benutzerkonto können
  damit nichts anfangen.
- Zugangsdaten liegen **nirgends im Klartext** auf der Platte. Ältere Versionen haben sie als Datei abgelegt
  (`%APPDATA%\Trainingsblick\config\strava.secrets.json`, `%USERPROFILE%\.garminconnect\garmin_tokens.json`); beim ersten
  Start übernimmt das Programm sie verschlüsselt und löscht die alten Dateien.
- Was DPAPI **nicht** verhindert (das kann kein Programm, auch kein Browser): Schadsoftware, die unter deinem eigenen
  Windows-Konto läuft. Halte Windows und deinen Virenschutz aktuell.
- Der Strava-Zugang darf nur **lesen** (deine Aktivitäten). Der Garmin-Schlüssel ist dagegen eine volle Anmeldung an deinem
  Garmin-Konto, deshalb ist er besonders geschützt. Du kannst ihn jederzeit unter **Körperdaten → Trennen** löschen.
- Das Programm ist nur auf deinem eigenen PC erreichbar (`127.0.0.1` mit Zufalls-Schlüssel), nicht aus dem Netzwerk.
- Zugriff widerrufen: Strava unter <https://www.strava.com/settings/apps>, Garmin durch Ändern des Passworts.

**Was wird ins Internet geschickt?**
- An **Strava**: nur Abrufe deiner eigenen Aktivitäten
- An **Open-Meteo** (kostenloser Wetterdienst): für das Wetter je Einheit nur das Datum und der Startort auf etwa 10 km gerundet
- An **Garmin**: nur wenn du es verbindest, deine Anmeldung und der Abruf deiner Tageswerte
- Kartenbilder kommen von **OpenStreetMap**
- An **GitHub**: einmal je Start die Frage, ob es eine neue Version gibt (mit der Versionsnummer, sonst nichts)

---

## Eigene Sounds für Videos (optional)

Ohne Zutun erzeugt das Programm die Sound-Effekte selbst. Wer eigene Sounds möchte, legt MP3-Dateien mit genau diesen Namen in
`%APPDATA%\Trainingsblick\ton`: `woosh.mp3`, `blop.mp3`, `klick.mp3`, `riser.mp3`, `impact.mp3`, `bling.mp3`.
Für Hintergrundmusik: `musik_lofi.mp3` und/oder `musik_daytona.mp3` (dann erscheint im Studio die Auswahl „Musik“).
Achte darauf, dass du die Sounds verwenden darfst.

---

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| „Der Computer wurde durch Windows geschützt“ beim Installieren | Auf **„Weitere Informationen“** und dann **„Trotzdem ausführen“** klicken. |
| Der Virenschutz meldet die Setup-Datei | Kommt bei neuen, unsignierten Programmen vor. Nur die Datei von der Release-Seite oben verwenden. |
| Strava: „Port 8123 ist belegt“ | Läuft Trainingsblick zweimal? Alle Fenster schließen und neu starten. |
| Strava: „redirect_uri invalid“ / „Bad Request“ | In der Strava-API-App muss bei **Authorization Callback Domain** genau `localhost` stehen. |
| Strava: „Der Zugriff auf Aktivitäten wurde nicht freigegeben“ | Beim Verbinden den Haken bei „Aktivitätsdaten ansehen“ setzen. |
| Strava antwortet mit „HTTP 429“ | Strava-Limit erreicht (zu viele Abrufe). Das Programm wartet von selbst und macht später weiter. |
| Es fehlen alte Einheiten | Unter **Einstellungen …** auf **„Alles neu laden …“** klicken. |
| Garmin: „Paket fehlt“ (nur beim Start aus dem Quellcode) | Unter **Körperdaten** auf **„Garmin-Paket installieren“** klicken. |
| Garmin-Anmeldung klappt nicht | Daten auf <https://connect.garmin.com> prüfen. Ist Zwei-Faktor aktiv, den Code aus Mail/App eingeben. |
| Video lässt sich nicht erstellen | Das Programm nutzt Microsoft Edge (oder Chrome) als Fenster. Edge aktualisieren. |
| Das Fenster ist weg, das Programm läuft aber noch | Im Task-Manager „pythonw.exe“ beenden und neu starten. |

Hilft das alles nicht: schreib eine Nachricht auf Instagram an [@tritopa](https://www.instagram.com/tritopa/). Am besten mit
einem Bildschirmfoto der Meldung und, falls vorhanden, dem neuesten Bericht aus `%APPDATA%\Trainingsblick\logs`
(der enthält keine Zugangsdaten).

---

## Deinstallieren

1. Windows-**Einstellungen → Apps → Installierte Apps**, „Trainingsblick“ → **Deinstallieren**
2. Die Frage, ob auch deine Daten und Zugänge gelöscht werden sollen, mit **„Ja“** beantworten
   (sonst bleiben `%APPDATA%\Trainingsblick` und `%LOCALAPPDATA%\Trainingsblick` für eine spätere Neuinstallation liegen)
3. Optional: auf <https://www.strava.com/settings/apps> den Zugriff von „Mein Dashboard“ widerrufen und die API-App löschen

---

## Für Entwickler

```
trainingsblick.py            Einstieg: Server mit RPC-Funktionen, Fenster (lib/webshell.py)
lib/strava_api.py              Strava-Anmeldung (OAuth, Callback localhost:8123) und Abrufe
lib/trainingsblick_logik.py  Aktivitäten holen und zwischenspeichern, Bestzeiten/Runden/Wetter im Hintergrund, Demo-Daten
lib/garmin_logik.py            Garmin Connect; Abruf in lib/garmin_helfer.py (Paket garminconnect, Python ≥ 3.12),
                               der Zugang geht nur über stdin/stdout an den Helfer, nie als Datei
lib/ablage.py                  Ordner öffnen; Speichern-Dialoge nur als Ersatzweg (normal speichert die Seite, ui/src/speichern.ts)
lib/orte.py                    Datenordner (%APPDATA%\Trainingsblick, macOS ~/Library/Application Support/Trainingsblick,
                               abweichend per TRAININGSBLICK_DATEN)
lib/tresor.py                  Zugangsdaten verschlüsselt (DPAPI) in %LOCALAPPDATA%\Trainingsblick\geheim,
                               macOS: im Schlüsselbund (lib/schluesselbund.py, Security.framework über ctypes)
lib/version.py, lib/update.py  Versionsnummer, Hinweis auf neue Releases
ui/                            Oberfläche: React + TypeScript + Vite
web/index.html                 fertiger Build der Oberfläche (eine Datei, mit eingecheckt)
installer/                     Installer: bauen.ps1 (eingebettetes Python + Inno Setup), trainingsblick.iss, symbol.py;
                               mac_app.py baut den Starter Trainingsblick.app für macOS
                               mac_bauen.py baut die eigenständige Mac-App samt .dmg (mac_starter.c: ihr Startprogramm)
.github/workflows/release.yml  baut bei einem Tag v<Version> die Setup.exe und legt das Release an
```

Aus dem Quellcode starten: `Trainingsblick starten.cmd` (legt `.venv` an), zum Ausprobieren `Demo starten.cmd`.
Auf dem Mac: `Trainingsblick starten.command` bzw. `Demo starten.command` (zusätzlich `requirements-mac.txt`: pywebview für das
eigene Fenster). Alles Mac-Spezifische hängt an `sys.platform == "darwin"`, der Windows-Weg ist unverändert.

Neues Release: `VERSION` in `lib/version.py` erhöhen, committen, dann `git tag v1.2.0` und `git push origin v1.2.0`.
Lokal bauen (braucht Python 3.12 und [Inno Setup 6](https://jrsoftware.org/isdl.php)):
`powershell -ExecutionPolicy Bypass -File installer\bauen.ps1`

Oberfläche bauen (Node.js 20 oder neuer):

```
cd ui
npm ci
npm run build
```

Ohne Fenster starten (gibt nur die Adresse aus): `.venv\Scripts\python trainingsblick.py --kein-fenster --demo --port 8800 --token test`
(Mac: `.venv/bin/python trainingsblick.py …`),
dann im Browser `http://127.0.0.1:8800/?t=test` öffnen.

Bilder und Videos zeichnet die Oberfläche selbst (Canvas). Videos entstehen Bild für Bild mit WebCodecs und
[Mediabunny](https://mediabunny.dev) als MP4 mit fester Bildrate. Die Zeichen- und Intervall-Logik ist eine Kopie aus der App
Formkurve (`ui/src/studio`, `ui/src/sammel`).

---

## Lizenz und Hinweise

Trainingsblick steht unter der [MIT-Lizenz](LICENSE): Du darfst es frei nutzen, weitergeben und verändern. Es gibt keine
Gewähr, dass alles fehlerfrei funktioniert.

Trainingsblick ist ein privates Projekt und **kein Produkt von Strava oder Garmin**. Es wird von ihnen weder unterstützt
noch geprüft. Strava ist eine Marke von Strava, Inc., Garmin eine Marke von Garmin Ltd. oder ihren Tochtergesellschaften.

Bis Version 1.0.1 hieß das Programm „Strava Dashboard“. Wer das installiert hat, führt einfach die neue Setup-Datei aus:
Sie ersetzt das alte Programm, und Einstellungen, Daten und Zugänge werden beim ersten Start übernommen.
