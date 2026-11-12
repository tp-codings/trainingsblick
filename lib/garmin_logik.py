"""Garmin-Anbindung fuers Trainingsblick.

Der eigentliche Abruf steckt in lib/garmin_helfer.py und wird mit einem Python >= 3.12 als Unterprozess gestartet.
Hier: Python finden, Paket pruefen/installieren, Anmeldung (inkl. Zwei-Faktor), Abruf im Hintergrund, Cache lesen.
Der Zugang liegt nur verschluesselt im Tresor; eine Klartext-Datei frueherer Versionen (~/.garminconnect) wird uebernommen
und geloescht.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import orte  # noqa: E402
import tresor  # noqa: E402

SCRIPT_DIR = orte.PROGRAMM
HELFER = SCRIPT_DIR / "lib" / "garmin_helfer.py"
CACHE = orte.CACHE / "garmin_tage.json"
MIN_PY = (3, 12)
VERALTET_S = 6 * 3600


def _flags():
    return 0x08000000 if os.name == "nt" else 0      # CREATE_NO_WINDOW


TRESOR = "garmin"       # Zugang (Token von garminconnect) verschluesselt im Tresor, nie als Datei im Klartext


def _tokens():
    return (tresor.lesen(TRESOR) or {}).get("tokens") or ""


def _alt_lesen(text):
    j = json.loads(text)
    return {"tokens": text.strip()} if isinstance(j, dict) and j.get("di_refresh_token") else None


def alt_uebernehmen(cfg):
    """Fruehere Versionen liessen garminconnect den Zugang im Klartext ablegen (cfg garmin_tokens oder ~/.garminconnect):
    einmalig in den Tresor uebernehmen, Datei loeschen, leeren Ordner entfernen."""
    ordner = Path(os.path.expanduser(cfg.get("garmin_tokens") or os.path.join("~", ".garminconnect")))
    tresor.uebernehmen(TRESOR, ordner / "garmin_tokens.json", _alt_lesen)
    try:
        ordner.rmdir()          # nur, wenn nichts anderes mehr drin liegt
    except OSError:
        pass
    cfg.pop("garmin_tokens", None)


def _tokens_merken(j):
    """Ereignis "tokens" vom Helfer: neuen bzw. erneuerten Zugang verschluesselt ablegen."""
    if j.get("ereignis") == "tokens" and j.get("daten"):
        tresor.schreiben(TRESOR, {"tokens": j["daten"]})


def _py_version(exe):
    try:
        r = subprocess.run([exe, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=20, creationflags=_flags())
        v = r.stdout.decode("utf-8", "replace").strip()
        a, b = v.split(".")
        return (int(a), int(b)) if r.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def finde_python(vorgabe=""):
    """(exe, 'x.y') des neuesten Python >= 3.12 oder None. Reihenfolge: Vorgabe aus der Konfiguration, py-Launcher, uebliche Orte."""
    kandidaten = []
    if vorgabe:
        kandidaten.append(vorgabe)
    # zuerst das Python, mit dem das Dashboard laeuft (bei der Installation per Start-Datei ist garminconnect dort schon drin)
    eigen = os.path.join(os.path.dirname(sys.executable), "python.exe" if os.name == "nt" else "python")
    eigen = eigen if os.path.isfile(eigen) else sys.executable
    v = _py_version(eigen)
    if not vorgabe and v and v >= MIN_PY:
        return eigen, "%d.%d" % v
    if os.name == "nt":
        for v in ("3.14", "3.13", "3.12"):
            try:
                r = subprocess.run(["py", "-" + v, "-c", "import sys;print(sys.executable)"], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, timeout=20, creationflags=_flags())
                exe = r.stdout.decode("utf-8", "replace").strip()
                if r.returncode == 0 and exe:
                    kandidaten.append(exe)
            except (OSError, subprocess.SubprocessError):
                pass
        la = os.environ.get("LOCALAPPDATA", "")
        for v in ("314", "313", "312"):
            for basis in (os.path.join(la, "Programs", "Python"), "C:\\Program Files", "C:\\"):
                for ordner in ("Python" + v, "Python" + v + "-64"):
                    kandidaten.append(os.path.join(basis, ordner, "python.exe"))
    else:
        for n in ("python3.14", "python3.13", "python3.12", "python3"):
            kandidaten.append(n)
        if sys.platform == "darwin":
            # aus dem Finder gestartet kennt der PATH weder Homebrew noch das Python von python.org
            for v in ("3.14", "3.13", "3.12"):
                kandidaten += ["/opt/homebrew/bin/python" + v, "/usr/local/bin/python" + v,
                               "/Library/Frameworks/Python.framework/Versions/%s/bin/python3" % v]
    gesehen = set()
    beste = None
    for k in kandidaten:
        if k in gesehen:
            continue
        gesehen.add(k)
        if os.name == "nt" and os.sep in k and not os.path.isfile(k):
            continue
        v = _py_version(k)
        if v and v >= MIN_PY and (beste is None or v > beste[1]):
            beste = (k, v)
    return (beste[0], "%d.%d" % beste[1]) if beste else None


class Garmin:
    """Zustand und Aktionen; alle langen Arbeiten laufen in Threads, die Oberflaeche fragt `zustand()` ab."""

    def __init__(self, cfg, stossen, demo=False):
        self.cfg, self.stossen, self.demo = cfg, stossen, demo
        self.lock = threading.Lock()
        self.proc = None
        self.z = {"py": "", "py_ver": "", "geprueft": False, "paket": None, "busy": False, "art": "", "text": "", "fehler": False,
                  "mfa": False, "fertig": 0, "gesamt": 0, "anmelden": False}
        self.ver = 0
        self.letzte = collections.deque(maxlen=6)
        if not demo:
            alt_uebernehmen(cfg)

    # ---- Zustand
    def tokens_da(self):
        return self.demo or tresor.vorhanden(TRESOR)

    def stand(self):
        try:
            return float(json.loads(CACHE.read_text(encoding="utf-8")).get("stand") or 0)
        except (OSError, ValueError, AttributeError):
            return 0.0

    def zustand(self):
        with self.lock:
            z = dict(self.z)
        z["verbunden"] = self.tokens_da()
        z["ver"] = self.ver
        z["stand"] = time.time() if self.demo else self.stand()
        return z

    def _set(self, **kw):
        with self.lock:
            self.z.update(kw)
        self.stossen()

    # ---- Pruefen / Installieren
    def pruefen(self):
        if self.demo:
            self._set(geprueft=True, py="demo", py_ver="3.12", paket=True)
            return
        self._set(busy=True, art="pruefen", text="Prüfe Python …", fehler=False)
        py = finde_python(self.cfg.get("garmin_python", ""))
        if not py:
            self._set(busy=False, art="", geprueft=True, py="", py_ver="", paket=None, fehler=True,
                      text="Kein Python 3.12 oder neuer gefunden.")
            return
        exe, ver = py
        ok, info = self._paket_pruefen(exe)
        self._set(busy=False, art="", geprueft=True, py=exe, py_ver=ver, paket=ok, fehler=False,
                  text="" if ok else "Das Paket garminconnect ist nicht installiert.")

    def _paket_pruefen(self, exe):
        try:
            r = subprocess.run([exe, str(HELFER), "pruefen"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
                               creationflags=_flags())
            for zeile in r.stdout.decode("utf-8", "replace").splitlines():
                try:
                    j = json.loads(zeile)
                except ValueError:
                    continue
                if j.get("ereignis") == "pruefen":
                    return bool(j.get("ok")), j
        except (OSError, subprocess.SubprocessError):
            pass
        return False, {}

    def installieren(self):
        if self.demo:
            return
        with self.lock:
            exe = self.z["py"]
            if self.z["busy"] or not exe:
                return
        self._set(busy=True, art="install", text="Installiere garminconnect …", fehler=False)
        try:
            # in einer venv (Installation per Start-Datei) ohne --user, sonst ins Benutzerverzeichnis
            venv = os.path.isfile(os.path.join(os.path.dirname(os.path.dirname(exe)), "pyvenv.cfg"))
            r = subprocess.run([exe, "-m", "pip", "install"] + ([] if venv else ["--user"]) + ["garminconnect==0.3.19"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900, creationflags=_flags())
            aus = r.stdout.decode("utf-8", "replace").strip().splitlines()
            if r.returncode != 0:
                self._set(busy=False, art="", fehler=True, text="Installation fehlgeschlagen: " + (aus[-1][:200] if aus else "unbekannt"))
                return
        except (OSError, subprocess.SubprocessError) as e:
            self._set(busy=False, art="", fehler=True, text="Installation fehlgeschlagen: %s" % e)
            return
        ok, _ = self._paket_pruefen(exe)
        self._set(busy=False, art="", paket=ok, fehler=not ok, text="" if ok else "Das Paket lässt sich nach der Installation nicht laden.")

    # ---- Unterprozess mit Ereignissen
    def _starte(self, argumente, stdin_zeilen=(), bei_ereignis=None):
        with self.lock:
            exe = self.z["py"]
        self.letzte.clear()
        p = subprocess.Popen([exe, "-X", "utf8", str(HELFER)] + argumente, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, creationflags=_flags(), cwd=str(SCRIPT_DIR))
        self.proc = p
        for zl in stdin_zeilen:
            p.stdin.write((json.dumps(zl, ensure_ascii=False) + "\n").encode("utf-8"))
        p.stdin.flush()
        endergebnis = {}
        for roh in iter(p.stdout.readline, b""):
            zeile = roh.decode("utf-8", "replace").strip()
            if not zeile:
                continue
            try:
                j = json.loads(zeile)
            except ValueError:
                self.letzte.append(zeile[:200])
                continue
            if j.get("ereignis") in ("fertig", "fehler"):
                endergebnis = j
            if bei_ereignis:
                bei_ereignis(j)
        p.wait()
        self.proc = None
        if not endergebnis:
            endergebnis = {"ereignis": "fehler", "text": ("Helfer beendet: " + self.letzte[-1]) if self.letzte else "Helfer ohne Antwort beendet"}
        return endergebnis

    # ---- Anmeldung
    def anmelden(self, email, passwort):
        with self.lock:
            if self.z["busy"] or not self.z["py"] or not self.z["paket"]:
                return
        if not email or not passwort:
            raise ValueError("E-Mail und Passwort eintragen")
        self._set(busy=True, art="login", text="Melde bei Garmin an …", fehler=False, mfa=False, anmelden=False)

        def ereignis(j):
            _tokens_merken(j)
            if j.get("ereignis") == "mfa":
                self._set(mfa=True, text="Bestätigungscode eingeben")

        def lauf():
            try:
                erg = self._starte(["login"], [{"email": email, "passwort": passwort}], ereignis)
            except Exception as e:    # noqa: BLE001
                erg = {"ereignis": "fehler", "text": str(e)}
            if erg.get("ereignis") == "fertig":
                self._set(busy=False, art="", mfa=False, fehler=False, text="Verbunden")
                self.sync()
            else:
                self._set(busy=False, art="", mfa=False, fehler=True, text=erg.get("text") or "Anmeldung fehlgeschlagen")
        threading.Thread(target=lauf, daemon=True).start()

    def mfa_code(self, code):
        p = self.proc
        if not p or not p.stdin:
            raise ValueError("Keine Anmeldung offen")
        try:
            p.stdin.write((json.dumps({"code": str(code).strip()}) + "\n").encode("utf-8"))
            p.stdin.flush()
        except OSError:
            raise ValueError("Anmeldung ist nicht mehr offen")
        self._set(mfa=False, text="Prüfe Code …")

    def trennen(self):
        tresor.loeschen(TRESOR)
        self._set(text="", fehler=False, anmelden=False)

    # ---- Abruf
    def sync(self, voll=False):
        if self.demo:
            return
        with self.lock:
            if self.z["busy"] or not self.z["py"] or not self.z["paket"]:
                return
        if not self.tokens_da():
            return
        self._set(busy=True, art="sync", text="Lade Garmin-Daten …", fehler=False, fertig=0, gesamt=0, anmelden=False)

        def ereignis(j):
            _tokens_merken(j)
            e = j.get("ereignis")
            if e == "start":
                self._set(gesamt=int(j.get("gesamt") or 0))
            elif e == "fortschritt":
                self._set(fertig=int(j.get("fertig") or 0), gesamt=int(j.get("gesamt") or 0))
                if int(j.get("fertig") or 0) % 5 == 0:
                    self.ver += 1
                    self.stossen()

        def lauf():
            argumente = ["sync", "--cache", str(CACHE), "--tage", "120"]
            if voll:
                argumente += ["--ab", (dt.date.today() - dt.timedelta(days=365)).isoformat()]
            try:
                erg = self._starte(argumente, [{"tokens": _tokens()}], ereignis)
            except Exception as e:    # noqa: BLE001
                erg = {"ereignis": "fehler", "text": str(e)}
            self.ver += 1
            if erg.get("ereignis") == "fertig":
                self._set(busy=False, art="", fehler=False, text="")
            else:
                self._set(busy=False, art="", fehler=True, text=erg.get("text") or "Abruf fehlgeschlagen", anmelden=bool(erg.get("anmelden")))
        threading.Thread(target=lauf, daemon=True).start()

    def hintergrund(self):
        """Beim Start: Python/Paket pruefen und, wenn verbunden und der Stand alt ist, nachladen."""
        try:
            self.pruefen()
            z = self.zustand()
            if z["verbunden"] and z["paket"] and time.time() - z["stand"] > VERALTET_S:
                self.sync()
        except Exception:    # noqa: BLE001
            pass

    def beenden(self):
        p = self.proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    # ---- Daten
    def daten(self):
        if self.demo:
            return demo_garmin()
        try:
            j = json.loads(CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"tage": [], "vo2": [], "stand": 0}
        return {"tage": sorted(j.get("tage", {}).items()), "vo2": sorted(j.get("vo2", {}).items()), "stand": j.get("stand", 0)}


def demo_garmin(tage=120):
    """Erfundene Erholungsdaten (passend zum Triathlon-Muster der Demo)."""
    rnd = random.Random(11)
    heute = dt.date.today()
    out, vo2 = [], []
    for i in range(tage, -1, -1):
        d = heute - dt.timedelta(days=i)
        woche = math.sin(i / 9.0)
        rhr = 49 + 3 * woche + rnd.uniform(-1.5, 1.5) - (tage - i) / tage * 2
        hrv = 66 - 6 * woche + rnd.uniform(-5, 5) + (tage - i) / tage * 4
        sl = 7.1 * 3600 + rnd.uniform(-1.1, 1.0) * 3600
        tief, rem = sl * rnd.uniform(.14, .2), sl * rnd.uniform(.18, .24)
        wach = sl * rnd.uniform(.04, .09)
        bb = 62 + 14 * math.cos(i / 6.0) + rnd.uniform(-6, 6)
        out.append([d.isoformat(), {
            "rhr": round(rhr), "hrv": round(hrv), "hrvw": round(hrv - 1), "hrvs": "BALANCED" if hrv > 55 else "LOW",
            "sl": round(sl), "tief": round(tief), "rem": round(rem), "leicht": round(sl - tief - rem - wach), "wach": round(wach),
            "slscore": round(max(40, min(98, 60 + (sl - 6.3 * 3600) / 3600 * 14 + rnd.uniform(-5, 5)))),
            "bbh": round(max(25, min(100, bb + 20))), "bbw": round(max(20, min(100, bb + 8))), "bbl": round(max(5, bb - 50)), "str": round(rnd.uniform(18, 42)),
            "schritte": round(rnd.uniform(5000, 16000)), "tr": round(max(8, min(98, 55 + 18 * math.cos(i / 6.0) + rnd.uniform(-9, 9)))),
            "trl": "HIGH"}])
        if i % 7 == 0:
            vo2.append([d.isoformat(), round(50.5 + (tage - i) / tage * 2.4 + rnd.uniform(-.2, .2), 1)])
    return {"tage": out, "vo2": vo2, "stand": time.time()}
