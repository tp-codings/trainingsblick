#!/bin/zsh
# Trainingsblick auf dem Mac starten (Doppelklick im Finder). Beim ersten Mal wird alles eingerichtet:
# eigene Python-Umgebung im Programmordner (.venv), Zusatzpakete, Starter "Trainingsblick.app".
# Das Gegenstueck zu "Trainingsblick starten.cmd" unter Windows.
cd "$(dirname "$0")" || exit 1

starten() {
    if [ -d "Trainingsblick.app" ]; then
        # -n: die Demo darf neben dem richtigen Programm laufen
        if [ $# -gt 0 ]; then open -n "Trainingsblick.app" --args "$@"; else open "Trainingsblick.app"; fi
    else
        nohup .venv/bin/python trainingsblick.py "$@" >/dev/null 2>&1 &
    fi
    echo
    echo "  Trainingsblick startet. Dieses Fenster kannst du schließen."
    echo "  Künftig genügt ein Doppelklick auf „Trainingsblick“ (Trainingsblick.app) in diesem Ordner;"
    echo "  die App lässt sich auch ins Dock ziehen."
    echo
    exit 0
}

neu_genug() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1 }

# Schon eingerichtet? Dann direkt starten.
if [ -x ".venv/bin/python" ] && neu_genug .venv/bin/python; then
    [ -d "Trainingsblick.app" ] || .venv/bin/python installer/mac_app.py >/dev/null 2>&1
    starten "$@"
fi

echo
echo "  Trainingsblick wird eingerichtet (nur beim ersten Start, dauert 1-2 Minuten) ..."
echo

# ---- Python 3.12 oder neuer suchen (das Python von macOS selbst ist zu alt)
python_suchen() {
    PY=""
    local k
    for k in python3.14 python3.13 python3.12 \
             /opt/homebrew/bin/python3.14 /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 \
             /usr/local/bin/python3.14 /usr/local/bin/python3.13 /usr/local/bin/python3.12 \
             /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
             /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
             /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 python3; do
        k="$(command -v "$k" 2>/dev/null)" || continue
        [ "$k" = /usr/bin/python3 ] && continue        # Platzhalter von macOS: zu alt, oder er will erst Xcode-Werkzeuge laden
        if neu_genug "$k"; then PY="$k"; return 0; fi
    done
    return 1
}

if ! python_suchen; then
    echo "  Python 3.12 oder neuer wurde nicht gefunden."
    echo
    BREW="$(command -v brew 2>/dev/null)"
    [ -z "$BREW" ] && [ -x /opt/homebrew/bin/brew ] && BREW=/opt/homebrew/bin/brew
    [ -z "$BREW" ] && [ -x /usr/local/bin/brew ] && BREW=/usr/local/bin/brew
    if [ -n "$BREW" ]; then
        read "antwort?  Soll Python jetzt automatisch installiert werden (mit Homebrew)? [j/N] "
        if [[ "$antwort" == [jJyY]* ]]; then
            "$BREW" install python@3.13
            python_suchen
        fi
    fi
    if [ -z "$PY" ]; then
        echo
        echo "  Bitte Python von https://www.python.org/downloads/macos/ installieren (Version 3.12 oder neuer,"
        echo "  „macOS 64-bit universal2 installer“) und danach diese Datei noch einmal doppelklicken."
        echo
        open "https://www.python.org/downloads/macos/"
        exit 1
    fi
fi

# ---- Eigene Python-Umgebung im Programmordner anlegen
echo "  Lege die Python-Umgebung an ..."
if ! "$PY" -m venv .venv; then
    echo
    echo "  Die Python-Umgebung konnte nicht angelegt werden. Liegt der Ordner vielleicht an einem"
    echo "  schreibgeschützten Ort? Dann den Ordner z. B. nach „Dokumente“ verschieben."
    echo
    rm -rf .venv
    exit 1
fi

echo "  Installiere Zusatzpakete ..."
if ! .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements-mac.txt; then
    echo
    echo "  Hinweis: Das Paket für das eigene Programmfenster ließ sich nicht installieren."
    echo "  Trainingsblick öffnet sich stattdessen im Browser (Edge/Chrome als eigenes Fenster, sonst als Tab)."
    echo
fi
if ! .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt; then
    echo
    echo "  Hinweis: Das Garmin-Paket ließ sich nicht installieren. Das Dashboard läuft trotzdem,"
    echo "  nur die Körperdaten von Garmin fehlen. Im Programm gibt es dafür einen Knopf „Garmin-Paket installieren“."
    echo
fi

# ---- Starter mit eigenem Symbol (wie die Verknüpfung auf dem Windows-Desktop)
if .venv/bin/python installer/mac_app.py >/dev/null; then
    echo "  Fertig. In diesem Ordner liegt jetzt „Trainingsblick“ (Trainingsblick.app)."
fi

starten "$@"
