# -*- coding: utf-8 -*-
"""
Dateien, die die Seite erzeugt hat (Bilder, Videos), per Speichern- bzw. Ordner-Dialog ablegen und Ordner zeigen.
Der Dialog (tkinter) laeuft in einem eigenen Prozess, damit das Dashboard-Fenster nicht haengt.
macOS: der Dialog des Systems, am eigenen Fenster (pywebview) bzw. ueber osascript; tkinter fehlt dort oft.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

STANDARD = Path.home() / "Pictures" / "Trainingsblick"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0

_DIALOG = (
    "import sys\nimport tkinter as tk\nfrom tkinter import filedialog\n"
    "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
    "art, start, titel, name = sys.argv[1:5]\n"
    "kw = dict(title=titel, initialdir=start or None, parent=r)\n"
    "if art == 'ordner':\n    p = filedialog.askdirectory(**kw)\n"
    "else:\n"
    "    import os\n    ext = os.path.splitext(name)[1].lower() or '.png'\n"
    "    p = filedialog.asksaveasfilename(initialfile=name, defaultextension=ext, filetypes=[(ext[1:].upper(), '*' + ext)], **kw)\n"
    "sys.stdout.buffer.write((p or '').encode('utf-8'))\n"
)


def _python_konsole():
    """python.exe neben dem laufenden Interpreter (unter pythonw.exe gaebe es keine Ausgabe)."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").is_file():
        return str(exe.parent / "python.exe")
    return str(exe)


_DIALOG_MAC = """on run argv
    set {art, startordner, titel, vorgabe} to argv
    tell current application to activate
    try
        if art is "ordner" then
            if startordner is "" then
                set ziel to choose folder with prompt titel
            else
                set ziel to choose folder with prompt titel default location (POSIX file startordner)
            end if
        else
            if startordner is "" then
                set ziel to choose file name with prompt titel default name vorgabe
            else
                set ziel to choose file name with prompt titel default name vorgabe default location (POSIX file startordner)
            end if
        end if
        return POSIX path of ziel
    on error number -128
        return ""
    end try
end run"""


def _dialog_mac(art, start, titel, name):
    """Dialog von macOS: am eigenen Fenster, wenn es eines gibt (pywebview), sonst ueber osascript (Fenster im Browser)."""
    pfad = None
    try:
        import webshell
        fenster = webshell.FENSTER.get("webview")
    except Exception:       # noqa: BLE001
        fenster = None
    if fenster is not None:
        try:
            import webview  # type: ignore
            if art == "ordner":
                pfad = fenster.create_file_dialog(webview.FileDialog.FOLDER, directory=start) or ""
            else:
                pfad = fenster.create_file_dialog(webview.FileDialog.SAVE, directory=start, save_filename=name) or ""
            if isinstance(pfad, (list, tuple)):
                pfad = pfad[0] if pfad else ""
            pfad = str(pfad)
        except Exception:       # noqa: BLE001
            pfad = None
    if pfad is None:
        try:
            p = subprocess.run(["/usr/bin/osascript", "-e", _DIALOG_MAC, art, start, titel, name],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900)
        except (OSError, subprocess.SubprocessError) as ex:
            raise ValueError("Auswahlfenster nicht möglich: %s" % ex)
        pfad = p.stdout.decode("utf-8", "replace").strip()
    endung = os.path.splitext(name)[1]
    if pfad and art != "ordner" and endung and not os.path.splitext(pfad)[1]:
        pfad += endung          # Endung im Dialog geloescht: wieder anhaengen, sonst erkennt kein Programm die Datei
    return pfad


def dialog(art, start, titel, name=""):
    """art: 'speichern' oder 'ordner'. -> gewaehlter Pfad oder '' (abgebrochen)"""
    if sys.platform == "darwin":
        pfad = _dialog_mac(art, start if os.path.isdir(start) else "", titel, name)
        return os.path.normpath(pfad) if pfad else ""
    try:
        p = subprocess.run([_python_konsole(), "-c", _DIALOG, art, start if os.path.isdir(start) else "", titel, name],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as ex:
        raise ValueError("Auswahlfenster nicht möglich: %s" % ex)
    pfad = p.stdout.decode("utf-8", "replace").strip()
    return os.path.normpath(pfad) if pfad else ""


def zeigen(pfad):
    """Ordner im Explorer (macOS: Finder) oeffnen (Datei: Ordner mit markierter Datei)."""
    p = Path(pfad)
    if not p.exists():
        p = p.parent if p.parent.exists() else STANDARD
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        if p.is_file():
            subprocess.Popen(["explorer", "/select,", str(p)])
        else:
            os.startfile(str(p))        # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(p)] if p.is_file() else ["open", str(p)])      # -R: im Finder markieren
    else:
        subprocess.Popen(["xdg-open", str(p)])


class Ablage:
    def __init__(self):
        self.letzter_ordner = None

    def _start(self):
        return str(self.letzter_ordner or STANDARD)

    def ablegen(self, quelle, name):
        quelle = Path(quelle)
        if not quelle.is_file():
            raise ValueError("Die Datei ist nicht angekommen")
        STANDARD.mkdir(parents=True, exist_ok=True)
        ziel = dialog("speichern", self._start(), "Speichern", name)
        if not ziel:
            return {"abgebrochen": True}
        try:
            Path(ziel).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(quelle), ziel)
        except OSError as e:
            raise ValueError("Speichern fehlgeschlagen: %s" % e)
        self.letzter_ordner = Path(ziel).parent
        return {"abgebrochen": False, "pfad": ziel}

    def ablegen_ordner(self, quellen):
        quellen = [Path(q) for q in quellen if Path(q).is_file()]
        if not quellen:
            raise ValueError("Die Bilder sind nicht angekommen")
        STANDARD.mkdir(parents=True, exist_ok=True)
        ordner = dialog("ordner", self._start(), "Ordner für die Bilder")
        if not ordner:
            return {"abgebrochen": True}
        ziel = Path(ordner)
        try:
            ziel.mkdir(parents=True, exist_ok=True)
            for q in quellen:
                shutil.move(str(q), str(ziel / q.name))
        except OSError as e:
            raise ValueError("Speichern fehlgeschlagen: %s" % e)
        self.letzter_ordner = ziel
        return {"abgebrochen": False, "ordner": str(ziel), "anzahl": len(quellen)}

    def ordner_zeigen(self, pfad=None):
        try:
            zeigen(pfad or self._start())
        except OSError as e:
            raise ValueError(str(e))
