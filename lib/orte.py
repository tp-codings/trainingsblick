# -*- coding: utf-8 -*-
"""
Wo das Dashboard seine Daten ablegt. Alles, was der Nutzer einstellt oder was geladen wurde, liegt AUSSERHALB des
Programmordners (Windows: %APPDATA%\\Trainingsblick, macOS: ~/Library/Application Support/Trainingsblick). So kann man den
Programmordner bei einem Update einfach ersetzen.

  DATEN    Grundordner (Umgebungsvariable TRAININGSBLICK_DATEN, sonst %APPDATA%\\Trainingsblick, macOS
           ~/Library/Application Support/Trainingsblick, sonst ~/.trainingsblick)
  CONFIG   Einstellungen (trainingsblick.json), nichts Geheimes
  GEHEIM   Zugangsdaten Strava und Garmin, verschluesselt (lib/tresor.py); Windows: %LOCALAPPDATA%\\Trainingsblick\\geheim.
           macOS legt sie in den Schluesselbund, der Ordner bleibt dort unbenutzt.
  CACHE    Zwischenspeicher (Aktivitaeten, Bestzeiten, Runden, Wetter, Garmin-Tage) - kann geloescht werden, laedt dann neu
  LOGS     Fehlerberichte
  TON      eigene Sounds fuer die Videos (<name>.mp3), optional

Bis Version 1.0.1 hiess das Programm "Strava Dashboard": Ordner %APPDATA%\\StravaDashboard und %LOCALAPPDATA%\\StravaDashboard
werden beim ersten Start einmalig umbenannt (_umziehen), die Einstellungsdatei strava_dashboard.json ebenso.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROGRAMM = Path(__file__).resolve().parent.parent
NAME = "Trainingsblick"
ALTER_NAME = "StravaDashboard"


def _umbenennen(alt: Path, neu: Path) -> None:
    if alt.exists() and not neu.exists():
        try:
            alt.rename(neu)
        except OSError:
            pass        # z. B. noch geoeffnet: dann beim naechsten Start


def _umziehen() -> None:
    """Ordner aus der Zeit als "Strava Dashboard" uebernehmen (Einstellungen, Daten, Zugaenge, Fensterprofil)."""
    if os.name != "nt" or (os.environ.get("TRAININGSBLICK_DATEN") or "").strip():
        return
    for var in ("APPDATA", "LOCALAPPDATA"):
        if os.environ.get(var):
            _umbenennen(Path(os.environ[var]) / ALTER_NAME, Path(os.environ[var]) / NAME)


def _daten() -> Path:
    eigen = (os.environ.get("TRAININGSBLICK_DATEN") or "").strip().strip('"')
    if eigen:
        return Path(eigen)
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAME
    return Path.home() / ".trainingsblick"


def _geheim() -> Path:
    """Zugangsdaten (verschluesselt, lib/tresor.py) lokal statt im mitwandernden Profil."""
    if (os.environ.get("TRAININGSBLICK_DATEN") or "").strip():
        return _daten() / "geheim"
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / NAME / "geheim"
    return _daten() / "geheim"


_umziehen()
DATEN = _daten()
GEHEIM = _geheim()
CONFIG = DATEN / "config"
CACHE = DATEN / "cache"
LOGS = DATEN / "logs"
TON = DATEN / "ton"
_umbenennen(CONFIG / "strava_dashboard.json", CONFIG / "trainingsblick.json")
