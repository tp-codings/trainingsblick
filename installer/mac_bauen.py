# -*- coding: utf-8 -*-
"""
macOS: eigenstaendige "Trainingsblick.app" samt Abbild zum Weitergeben bauen
(installer/build/Trainingsblick-<Version>-mac-<arch>.dmg). Das Gegenstueck zu installer/bauen.ps1 unter Windows.

Die App bringt alles mit: wer sie bekommt, zieht sie aus dem Abbild in "Programme" und startet sie; Python muss dort
nicht installiert sein.

  1. Python "standalone" (github.com/astral-sh/python-build-standalone; fest: PY_VERSION/PY_STAND, Pruefsumme PY_SHA256)
     nach Trainingsblick.app/Contents/Resources/python, ohne das, was das Programm nicht braucht (Tk, IDLE, pip ...)
  2. Pakete aus installer/abhaengigkeiten-mac.txt als fertige Wheels nach .../python/lib/python3.x/site-packages
  3. Programmdateien (trainingsblick.py, lib, web/index.html) nach Contents/Resources/app, Symbol, Info.plist
  4. Startprogramm Contents/MacOS/Trainingsblick aus installer/mac_starter.c (braucht clang: Xcode-Werkzeuge)
  5. alles vorab zu .pyc uebersetzen (die App schreibt spaeter nichts in sich hinein) und signieren (ad hoc)
  6. Kurztest: Demo-Server ueber das Startprogramm starten und /api/start abfragen, Garmin-Helfer pruefen
  7. Abbild (.dmg) mit der App und einem Verweis auf "Programme"

Aufruf:  python installer/mac_bauen.py [--arch arm64|x86_64] [--ohne-dmg]
         (--arch: Vorgabe ist der Prozessor dieses Macs; arm64 = Apple Silicon, x86_64 = Intel. Der Kurztest laeuft nur,
         wenn dieser Mac die gebaute Sorte auch ausfuehren kann.)
Braucht: Python 3.12+ mit pip zum Herunterladen der Pakete (z. B. .venv/bin/python), clang, Internet beim ersten Mal.
Die Oberflaeche wird NICHT gebaut: web/index.html ist eingecheckt (vorher ggf. "cd ui; npm run build").

Nicht dabei: eine Signatur mit Apple-Entwicklerkonto samt Beglaubigung (Notarization). Ohne sie fragt macOS beim ersten
Start einer aus dem Netz geladenen oder per AirDrop erhaltenen App nach (Systemeinstellungen > Datenschutz & Sicherheit >
"Dennoch oeffnen"). Mit Konto: SIGNATUR unten auf "Developer ID Application: ..." setzen und das .dmg mit
"xcrun notarytool submit" einreichen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import plistlib
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(WURZEL / "lib"))
import symbol  # noqa: E402
import version  # noqa: E402

NAME = "Trainingsblick"
KENNUNG = "io.github.tp-codings.trainingsblick"
SIGNATUR = "-"                      # "-" = ad hoc (ohne Apple-Entwicklerkonto)
MIN_MACOS = "11.0"

PY_VERSION = "3.13.18"
PY_STAND = "20261110"
PY_KURZ = "python" + ".".join(PY_VERSION.split(".")[:2])
# SHA256 laut Release-Seite (github.com/astral-sh/python-build-standalone/releases/tag/<PY_STAND>)
PY_SHA256 = {
    "arm64": ("aarch64", "7a2384641584ab9984221fcb0fc9265df465922af71be71410529e2a9c3f0540"),
    "x86_64": ("x86_64", "d27d59a722db9f69926eb6d9564071247221f45a04da920ea7f3001c97e32f9b"),
}

BUILD = HIER / "build"                # hier landet das fertige .dmg
# Gebaut wird in einem Ordner unter /tmp: liegt der Programmordner in iCloud (Schreibtisch, Dokumente), haengt macOS
# dort Dateien laufend Finder-Angaben an, und damit laesst sich eine App nicht signieren.
WERK = Path(tempfile.gettempdir()).resolve() / "trainingsblick-bau"
CACHE = HIER / "cache"

# Teile von Python, die das Programm nicht braucht (macht die App rund 25 MB kleiner)
UNNOETIG_LIB = ["itcl4*", "libtcl*", "tcl9*", "thread3*", "tk9*", "pkgconfig"]
UNNOETIG_STD = ["idlelib", "tkinter", "turtledemo", "turtle.py", "ensurepip", "test", "lib2to3", "pydoc_data",
                "config-*-darwin", "site-packages/pip", "site-packages/pip-*", "lib-dynload/_tkinter*"]
UNNOETIG_BIN = ["idle*", "pip*", "pydoc*", "*-config"]
# Pakete ohne fertiges Wheel (reines Python): werden vorab aus dem Quelltext zu einem Wheel gemacht
NUR_QUELLTEXT = ("proxy_tools",)


def lauf(*befehl, **kw):
    r = subprocess.run([str(b) for b in befehl], **kw)
    if r.returncode:
        raise SystemExit("Fehlgeschlagen (%d): %s" % (r.returncode, " ".join(str(b) for b in befehl)))
    return r


def python_holen(arch: str) -> Path:
    """Archiv mit dem eigenstaendigen Python (aus dem Zwischenspeicher oder von GitHub), Pruefsumme abgeglichen."""
    sorte, soll = PY_SHA256[arch]
    name = "cpython-%s+%s-%s-apple-darwin-install_only_stripped.tar.gz" % (PY_VERSION, PY_STAND, sorte)
    datei = CACHE / name
    CACHE.mkdir(parents=True, exist_ok=True)
    if not datei.exists():
        print("Lade Python %s (%s) ..." % (PY_VERSION, arch))
        url = "https://github.com/astral-sh/python-build-standalone/releases/download/%s/%s" % (PY_STAND, name.replace("+", "%2B"))
        teil = datei.with_suffix(".teil")
        with urllib.request.urlopen(url, timeout=120) as r, open(teil, "wb") as f:
            shutil.copyfileobj(r, f)
        teil.rename(datei)
    ist = hashlib.sha256(datei.read_bytes()).hexdigest()
    if ist != soll:
        datei.unlink()
        raise SystemExit("Pruefsumme von %s stimmt nicht (%s)" % (name, ist))
    return datei


def weg(ordner: Path, muster) -> None:
    for m in muster:
        for p in ordner.glob(m):
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
            else:
                p.unlink()


def app_bauen(arch: str) -> Path:
    app = WERK / (NAME + ".app")
    inhalt = app / "Contents"
    res = inhalt / "Resources"
    (inhalt / "MacOS").mkdir(parents=True)
    res.mkdir()

    # ---- 1. eingebautes Python
    with tarfile.open(python_holen(arch)) as t:
        t.extractall(res, filter="tar")                 # entpackt nach res/python
    py = res / "python"
    std = py / "lib" / PY_KURZ
    kopf = py / "include" / PY_KURZ                     # nur zum Bauen des Startprogramms noetig
    weg(py / "lib", UNNOETIG_LIB)
    weg(std, UNNOETIG_STD)
    weg(py / "bin", UNNOETIG_BIN)
    shutil.rmtree(py / "share", ignore_errors=True)

    # ---- 2. Pakete (nur fertige Wheels fuer macOS, CPython 3.x, diese Prozessorsorte)
    print("Installiere Pakete ...")
    sp = std / "site-packages"
    raeder = CACHE / "wheels"
    for zeile in (HIER / "abhaengigkeiten-mac.txt").read_text("utf-8").splitlines():
        if zeile.split("==")[0].strip() in NUR_QUELLTEXT:
            lauf(sys.executable, "-m", "pip", "wheel", "--disable-pip-version-check", "--quiet", "--no-deps",
                 "--wheel-dir", raeder, zeile.strip())
    lauf(sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-compile", "--quiet",
         "--target", sp, "--only-binary=:all:", "--find-links", raeder, "--platform", "macosx_%s_%s" % (MIN_MACOS.replace(".", "_"), arch),
         "--python-version", ".".join(PY_VERSION.split(".")[:2]), "--implementation", "cp",
         "-r", HIER / "abhaengigkeiten-mac.txt")
    shutil.rmtree(sp / "bin", ignore_errors=True)
    shutil.rmtree(sp / "PyObjCTest", ignore_errors=True)        # Selbsttests von pyobjc, 16 MB

    # ---- 3. Programmdateien, Symbol, Info.plist
    prog = res / "app"
    (prog / "lib").mkdir(parents=True)
    (prog / "web").mkdir()
    for n in ("trainingsblick.py", "README.md", "LICENSE"):
        shutil.copy2(WURZEL / n, prog / n)
    for f in sorted((WURZEL / "lib").glob("*.py")):
        shutil.copy2(f, prog / "lib" / f.name)
    shutil.copy2(WURZEL / "web" / "index.html", prog / "web" / "index.html")
    (res / (NAME + ".icns")).write_bytes(symbol.icns())
    with open(inhalt / "Info.plist", "wb") as f:
        plistlib.dump({
            "CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleExecutable": NAME, "CFBundleIconFile": NAME,
            "CFBundleIdentifier": KENNUNG, "CFBundlePackageType": "APPL", "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleShortVersionString": version.VERSION, "CFBundleVersion": version.VERSION,
            "CFBundleDevelopmentRegion": "de", "LSMinimumSystemVersion": MIN_MACOS, "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.healthcare-fitness",
            "NSHumanReadableCopyright": "MIT-Lizenz, github.com/" + version.REPO,
        }, f)

    # ---- 4. Startprogramm
    print("Baue das Startprogramm ...")
    lauf("clang", "-arch", arch, "-mmacosx-version-min=" + MIN_MACOS, "-O2", "-Wall", "-I", kopf,
         HIER / "mac_starter.c", "-o", inhalt / "MacOS" / NAME, "-L", py / "lib", "-l" + PY_KURZ,
         "-Wl,-rpath,@executable_path/../Resources/python/lib")
    shutil.rmtree(py / "include")

    # ---- 5. vorab uebersetzen (unchecked-hash: gilt unabhaengig vom Dateidatum), dann signieren
    print("Uebersetze und signiere ...")
    eigenes = py / "bin" / "python3"
    if laeuft_hier(arch):
        lauf(eigenes, "-I", "-m", "compileall", "-q", "--invalidation-mode", "unchecked-hash", std, prog,
             stdout=subprocess.DEVNULL)
    for p in app.rglob(".DS_Store"):
        p.unlink()
    lauf("xattr", "-cr", app)                           # Finder-Angaben u. ae. vertraegt die Signatur nicht
    lauf("codesign", "--force", "--deep", "--sign", SIGNATUR, "--identifier", KENNUNG, app,
         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lauf("codesign", "--verify", "--deep", "--strict", app)
    return app


def laeuft_hier(arch: str) -> bool:
    return platform.machine() == arch


def kurztest(app: Path) -> None:
    """Demo ohne Fenster ueber das Startprogramm, eigener Datenordner; dazu der Garmin-Helfer mit dem Python der App."""
    print("Kurztest ...")
    umgebung = dict(os.environ, TRAININGSBLICK_DATEN=str(WERK / "testdaten"))
    port = random.randint(20000, 40000)
    fehler = WERK / "test_fehler.txt"
    with open(fehler, "wb") as f:
        p = subprocess.Popen([str(app / "Contents" / "MacOS" / NAME), "--kein-fenster", "--demo", "--port", str(port),
                              "--token", "probe"], env=umgebung, stdout=subprocess.DEVNULL, stderr=f)
    try:
        ok = False
        for _ in range(40):
            time.sleep(0.5)
            try:
                req = urllib.request.Request("http://127.0.0.1:%d/api/start?t=probe" % port, data=b"{}", method="POST")
                with urllib.request.urlopen(req, timeout=5) as r:
                    if r.status == 200 and json.loads(r.read().decode("utf-8")).get("demo") is True:
                        ok = True
                        break
            except (OSError, ValueError):
                pass
        if not ok:
            raise SystemExit("Kurztest fehlgeschlagen: " + fehler.read_text("utf-8", "replace"))
    finally:
        p.terminate()
    res = app / "Contents" / "Resources"
    g = lauf(res / "python" / "bin" / "python3", "-X", "utf8", res / "app" / "lib" / "garmin_helfer.py", "pruefen",
             stdout=subprocess.PIPE, env=dict(umgebung, PYTHONDONTWRITEBYTECODE="1")).stdout.decode("utf-8", "replace").strip()
    if '"ok": true' not in g:
        raise SystemExit("Garmin-Helfer findet garminconnect nicht: " + g)
    shutil.rmtree(WERK / "testdaten", ignore_errors=True)
    fehler.unlink(missing_ok=True)
    lauf("codesign", "--verify", "--deep", "--strict", app)        # der Test hat nichts in die App geschrieben
    print("Kurztest ok (%s)" % g)


def dmg_bauen(app: Path, arch: str) -> Path:
    ziel = BUILD / ("%s-%s-mac-%s.dmg" % (NAME, version.VERSION, arch))
    stufe = WERK / "dmg"
    stufe.mkdir()
    lauf("ditto", app, stufe / app.name)                # ditto erhaelt Signatur und Verweise
    os.symlink("/Applications", stufe / "Applications")
    lauf("hdiutil", "create", "-volname", NAME, "-srcfolder", stufe, "-fs", "HFS+", "-format", "UDZO",
         "-imagekey", "zlib-level=9", "-ov", ziel, stdout=subprocess.DEVNULL)
    shutil.rmtree(stufe)
    return ziel


def main() -> None:
    ap = argparse.ArgumentParser(description="Eigenstaendige Mac-App und .dmg bauen")
    ap.add_argument("--arch", choices=sorted(PY_SHA256), default=platform.machine() if platform.machine() in PY_SHA256 else "arm64")
    ap.add_argument("--ohne-dmg", action="store_true")
    a = ap.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("Nur unter macOS.")
    print("%s %s (%s)" % (NAME, version.VERSION, a.arch))
    for ordner in (BUILD, WERK):
        if ordner.exists():
            shutil.rmtree(ordner)
        ordner.mkdir(parents=True)
    app = app_bauen(a.arch)
    if laeuft_hier(a.arch):
        kurztest(app)
    else:
        print("Kurztest uebersprungen: dieser Mac kann %s nicht ausfuehren." % a.arch)
    if a.ohne_dmg:
        print("Fertig (ohne .dmg): %s" % app)
        return
    dmg = dmg_bauen(app, a.arch)
    shutil.rmtree(WERK)
    print("Fertig: %s" % dmg)


if __name__ == "__main__":
    main()
