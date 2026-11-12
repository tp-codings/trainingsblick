# -*- coding: utf-8 -*-
"""
macOS: "Trainingsblick.app" bauen, das Gegenstueck zur Verknuepfung auf dem Windows-Desktop. Die App ist nur ein Starter
(Symbol + kleines Startskript); sie ruft das Python aus dem Programmordner (.venv) mit trainingsblick.py auf.

Damit das Programm im Dock, in der Menueleiste und in Nachfragen von macOS als "Trainingsblick" erscheint (und nicht als
"Python"), liegt in der App ein Verweis auf das eigentliche Python-Programm: macOS ordnet ein laufendes Programm dem
Buendel zu, aus dem es gestartet wurde. __PYVENV_LAUNCHER__ sagt Python dabei, dass es die Umgebung .venv benutzen soll
(so startet auch .venv/bin/python selbst). Fehlt der Verweis oder zeigt er ins Leere, startet .venv/bin/python direkt.

Die App findet den Programmordner, solange sie darin liegt; wird sie woanders hingezogen (z. B. nach "Programme"), nimmt
sie den Ordner, in dem sie gebaut wurde.

Aufruf:  python installer/mac_app.py [zielordner]      (macht "Trainingsblick starten.command"; Vorgabe: Programmordner)
"""
from __future__ import annotations

import os
import plistlib
import shutil
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(WURZEL / "lib"))
import symbol  # noqa: E402
import version  # noqa: E402

NAME = "Trainingsblick"

STARTER = """#!/bin/sh
# Startet Trainingsblick mit dem Python aus dem Programmordner (.venv). Erzeugt von installer/mac_app.py.
ORDNER=%(ordner)s
HIER="$(cd "$(dirname "$0")/../../.." 2>/dev/null && pwd)"
[ -f "$HIER/trainingsblick.py" ] && ORDNER="$HIER"
if [ ! -x "$ORDNER/.venv/bin/python" ] || [ ! -f "$ORDNER/trainingsblick.py" ]; then
    /usr/bin/osascript -e 'display alert "Trainingsblick" message "Der Programmordner wurde nicht gefunden oder ist noch nicht eingerichtet. Bitte im Programmordner „Trainingsblick starten.command“ doppelklicken." as critical' >/dev/null 2>&1
    exit 1
fi
cd "$ORDNER" || exit 1
PY="$(dirname "$0")/python"
if [ -x "$PY" ]; then
    __PYVENV_LAUNCHER__="$ORDNER/.venv/bin/python" exec "$PY" "$ORDNER/trainingsblick.py" "$@"
fi
exec "$ORDNER/.venv/bin/python" "$ORDNER/trainingsblick.py" "$@"
"""


def _sh(text):
    """Text als ein Wort fuer die Shell (einfache Anfuehrungszeichen)."""
    return "'" + str(text).replace("'", "'\\''") + "'"


def _python_programm():
    """Das eigentliche Python-Programm hinter .venv/bin/python (dort liegt nur ein Verweis auf ein Startprogramm).
    Bei Python von Homebrew und python.org steckt es als Python.app im Framework; der Pfad ueber "opt" bleibt bei
    kleinen Updates von Homebrew gueltig."""
    app = os.path.join(sys.base_prefix, "Resources", "Python.app", "Contents", "MacOS", "Python")
    if os.path.isfile(app):
        return app
    basis = getattr(sys, "_base_executable", "") or sys.executable
    return os.path.realpath(basis) if os.path.isfile(basis) else ""


def bauen(ziel: Path) -> Path:
    app = ziel / (NAME + ".app")
    if app.exists():
        shutil.rmtree(app)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({
            "CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleExecutable": NAME, "CFBundleIconFile": NAME,
            "CFBundleIdentifier": "io.github.tp-codings.trainingsblick", "CFBundlePackageType": "APPL",
            "CFBundleInfoDictionaryVersion": "6.0", "CFBundleShortVersionString": version.VERSION,
            "CFBundleVersion": version.VERSION, "LSMinimumSystemVersion": "11.0", "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.healthcare-fitness",
        }, f)
    (app / "Contents" / "Resources" / (NAME + ".icns")).write_bytes(symbol.icns())
    starter = app / "Contents" / "MacOS" / NAME
    starter.write_text(STARTER % {"ordner": _sh(WURZEL)}, encoding="utf-8")
    os.chmod(starter, 0o755)
    python = _python_programm()
    if python:
        os.symlink(python, app / "Contents" / "MacOS" / "python")
    return app


if __name__ == "__main__":
    print(bauen(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else WURZEL))
