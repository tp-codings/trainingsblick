# -*- coding: utf-8 -*-
"""
webshell.py - gemeinsamer Unterbau fuer Scripts mit React-Oberflaeche (Design wie Content Studio).

Ein Script liefert nur seine RPC-Tabelle {name: funktion(dict) -> dict} und den Pfad zur gebauten index.html.
Hier steckt alles andere: lokaler HTTP-Server (127.0.0.1, Token), Fenster (pywebview -> Edge/Chrome --app ->
Standardbrowser), Heartbeat (ping/beenden) und gemerkte Fenstergroesse.
macOS: pywebview oeffnet ein eigenes Fenster (WebKit) mit eigenem Namen in der Menueleiste; ohne pywebview wird ein
installierter Chromium-Browser (Edge, Chrome, Brave ...) im App-Modus genommen, sonst der Standardbrowser.

    import webshell
    sys.exit(webshell.starten(funktionen=..., ui_datei=Path(...), titel="...", profil="NucZugriff",
                              geo=gespeicherte_geometrie, argv=sys.argv[1:], busy=lambda: 0))

ValueError in einer Funktion -> HTTP 400 {"fehler": text} (die Oberflaeche zeigt es als Hinweis).
Aufrufparameter fuer Tests: --port N, --token T, --kein-fenster (nur Server, URL wird ausgegeben).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


# --------------------------------------------------------------------------- #
#  Eigenes Symbol je Script (Taskleiste von Shelf, Alt+Tab, Fenstersymbol)
# --------------------------------------------------------------------------- #
# Ohne eigenes Symbol landen alle Script-Fenster unter dem Browser-Symbol (Edge/Chrome im App-Modus). Jedes Script
# bekommt deshalb ein Symbol: farbiges Quadrat mit Strich-Piktogramm (24er-Raster, weiss). Die Seite zeigt es als
# Favicon (= Fenstersymbol), und das Fenster meldet sich bei Shelf an (%LOCALAPPDATA%\Shelf\fenster\<profil>.json),
# damit die Taskleiste dort einen eigenen Knopf mit diesem Symbol zeigt.
# Nur Pfade, Kreise und Rechtecke: Shelf zeichnet das SVG mit Direct2D, das keinen Text kann.
SYMBOLE = {
    "AppStarter": ("#2457f5", '<path d="M9 6.5v11l8.5-5.5z" fill="#fff"/>'),
    "GitGui": ("#3f3f46", '<circle cx="7" cy="5.5" r="2"/><circle cx="7" cy="18.5" r="2"/><circle cx="17" cy="7.5" r="2"/>'
                          '<path d="M7 7.5v9M17 9.5c0 4.5-10 2.5-10 7"/>'),
    "DopusGitBackup": ("#52525b", '<rect x="3.5" y="4" width="17" height="5" rx="1.5"/><path d="M5 9v9.5a1.5 1.5 0 0 0 1.5 1.5h11'
                                  'a1.5 1.5 0 0 0 1.5-1.5V9M10 13h4"/>'),
    "OrdnerVisualizer": ("#0891b2", '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z'
                                    'M8.5 16v-3M12 16v-5M15.5 16v-2"/>'),
    "FootageTagger": ("#7c3aed", '<path d="M3.5 12.5V4.5h8l9 9-8 8z"/><circle cx="8" cy="9" r="1.6"/>'),
    "KeyMaster": ("#b45309", '<circle cx="8" cy="15.5" r="4"/><path d="M11 12.5l8.5-8.5M16.5 7l2.5 2.5M14 9.5l2 2"/>'),
    "NucZugriff": ("#0d9488", '<rect x="4" y="4" width="16" height="7" rx="2"/><rect x="4" y="13" width="16" height="7" rx="2"/>'
                              '<path d="M8 7.5h.01M8 16.5h.01"/>'),
    "OllamaManager": ("#27272a", '<path d="M4.5 5.5h15v10.5H10l-5.5 4z"/><path d="M9 10.5h.01M12 10.5h.01M15 10.5h.01"/>'),
    "PfadeAbgleichen": ("#0369a1", '<path d="M4 8h15M15.5 4.5 19 8l-3.5 3.5M20 16H5M8.5 12.5 5 16l3.5 3.5"/>'),
    "PythonManager": ("#3776ab", '<path d="M8.5 7 3.5 12l5 5M15.5 7l5 5-5 5M13.5 5l-3 14"/>'),
    "ResolveTools": ("#dc2626", '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M8 5v14M16 5v14M3.5 12h17"/>'),
    "ResolvePacks": ("#be123c", '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9"/>'),
    "Trainingsblick": ("#1f8fc4", '<path d="M3.5 20h17M6.5 20v-6M11 20V6M15.5 20v-9M20 20V9"/>'),
    "StravaShare": ("#f97316", '<circle cx="17.5" cy="5.5" r="2.5"/><circle cx="6.5" cy="12" r="2.5"/><circle cx="17.5" cy="18.5" r="2.5"/>'
                               '<path d="M8.7 10.7l6.6-3.9M8.7 13.3l6.6 3.9"/>'),
    "SyncthingStatus": ("#0e7490", '<path d="M19.5 10.5A7.5 7.5 0 0 0 6 7L4 9M4 4v5h5M4.5 13.5A7.5 7.5 0 0 0 18 17l2-2M20 20v-5h-5"/>'),
    "TerminalEditor": ("#18181b", '<path d="M5 7l5 5-5 5M12.5 18h7"/>'),
    "VideoDownloader": ("#db2777", '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>'),
    "ArchivWaechter": ("#15803d", '<path d="M12 3l8 3v6c0 4.8-3.4 8-8 9-4.6-1-8-4.2-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>'),
    "InboxSortieren": ("#4f46e5", '<path d="M3.5 13.5 6.5 5h11l3 8.5V19h-17zM3.5 13.5h5l1 2.5h5l1-2.5h5"/>'),
}
_FARBEN = ["#2457f5", "#0d9488", "#7c3aed", "#ea580c", "#db2777", "#0891b2", "#15803d", "#b45309", "#4f46e5", "#be123c"]
_FENSTER_SYMBOL = '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M3.5 9h17"/>'


def symbol_svg(profil: str) -> str:
    """SVG (64x64) des Script-Symbols; unbekannte Scripts bekommen ein Fenster-Piktogramm in einer festen Farbe."""
    farbe, inhalt = SYMBOLE.get(profil) or (_FARBEN[int(hashlib.md5(profil.encode()).hexdigest(), 16) % len(_FARBEN)], _FENSTER_SYMBOL)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
            f'<rect width="64" height="64" rx="15" fill="{farbe}"/>'
            '<g transform="translate(14 14) scale(1.5)" fill="none" stroke="#fff" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{inhalt}</g></svg>')


def mit_symbol(html: bytes, profil: str) -> bytes:
    """Favicon in die Seite setzen: Edge/Chrome nehmen es im App-Modus als Fenster- und Taskleistensymbol."""
    if not profil or b"</head>" not in html:
        return html
    daten = base64.b64encode(symbol_svg(profil).encode("utf-8"))
    return html.replace(b"</head>", b'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,' + daten + b'"></head>', 1)


def _shelf_ordner() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")) / "Shelf" / "fenster"


_FENSTER_PID = {"pid": 0}      # vom Browser-Start gesetzt (Edge/Chrome laeuft mit eigenem Profil als eigener Prozess)
MAC = sys.platform == "darwin"
FENSTER = {"webview": None}    # das pywebview-Fenster, solange es offen ist (lib/ablage.py: Speichern-Dialoge am Fenster)


def _fenster_von(pids, titel: str):
    """Sichtbares Hauptfenster (mit Titelleiste) eines der Prozesse; ohne Treffer eines mit passendem Titel."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    u.GetWindow.restype = wintypes.HWND
    treffer = []
    proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _l):
        if not u.IsWindowVisible(h) or u.GetWindow(h, 4):            # 4 = GW_OWNER
            return True
        if not (u.GetWindowLongW(h, -16) & 0x00C00000):              # WS_CAPTION
            return True
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        n = u.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        if pid.value in pids:
            treffer.append((0, h, pid.value))
        elif titel and buf.value.startswith(titel):
            treffer.append((1, h, pid.value))
        return True
    u.EnumWindows(proto(cb), 0)
    treffer.sort(key=lambda t: t[0])
    return (treffer[0][1], treffer[0][2]) if treffer else (None, 0)


def fenster_melden(titel: str, profil: str, sekunden: float = 25.0) -> None:
    """Im Hintergrund das Fenster des Scripts suchen und bei Shelf anmelden (eigener Knopf mit eigenem Symbol).
    Nur wenn Shelf (Taskleisten-Programm) installiert ist, sonst passiert nichts."""
    if os.name != "nt" or not profil or not _shelf_ordner().parent.is_dir():
        return

    def arbeit():
        ende = time.time() + sekunden
        while time.time() < ende:
            time.sleep(0.4)
            try:
                pids = {p for p in (os.getpid(), _FENSTER_PID["pid"]) if p}
                hwnd, pid = _fenster_von(pids, titel)
            except Exception:    # noqa: BLE001
                return
            if not hwnd:
                continue
            try:
                ordner = _shelf_ordner()
                ordner.mkdir(parents=True, exist_ok=True)
                (ordner / f"{profil}.svg").write_text(symbol_svg(profil), encoding="utf-8")
                tmp = ordner / f"{profil}.json.tmp"
                tmp.write_text(json.dumps({"hwnd": int(hwnd), "pid": int(pid), "id": profil, "name": titel,
                                           "symbol": str(ordner / f"{profil}.svg")}), encoding="utf-8")
                os.replace(tmp, ordner / f"{profil}.json")
            except OSError:
                pass
            return
    threading.Thread(target=arbeit, daemon=True).start()


def fenster_abmelden(profil: str) -> None:
    try:
        (_shelf_ordner() / f"{profil}.json").unlink()
    except OSError:
        pass


# RPC-Aufrufe von aussen (Shelf), die den Takt NICHT verlaengern: sonst bliebe der Starter nach dem Schliessen des Fensters
# fuer immer am Leben.
PASSIV_API = {"uebersicht", "zustand_still"}


class _Takt:
    letzter_ping = time.time()


def _handler(funktionen, token, ui_datei: Path, beenden, profil: str = "", dateien=None, seitentitel: str = ""):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _senden(self, code, daten: bytes, typ="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(daten)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(daten)

        def _ok(self):
            u = urlparse(self.path)
            t = parse_qs(u.query).get("t", [""])[0] or self.headers.get("X-Token", "")
            return u, secrets.compare_digest(t, token)

        def do_GET(self):
            u, ok = self._ok()
            if u.path in ("/", "/index.html"):
                if not ok:
                    return self._senden(403, b"Zugriff nur mit Token", "text/plain")
                try:
                    html = mit_symbol(ui_datei.read_bytes().replace(b"__TOKEN__", token.encode()), profil)
                    if seitentitel:
                        import re as _re
                        html = _re.sub(rb"<title>[^<]*</title>", ("<title>%s</title>" % seitentitel).encode("utf-8"), html, count=1)
                except OSError:
                    return self._senden(500, f"Oberfläche fehlt: {ui_datei}".encode(), "text/plain; charset=utf-8")
                return self._senden(200, html, "text/html; charset=utf-8")
            if u.path == "/datei" and ok and dateien is not None:
                return self._datei(u)
            self._senden(404, b"{}")

        def _datei(self, u):
            """Lokale Datei ausliefern (Vorschaubilder, Ton): dateien(abfrage) -> (Pfad, Inhaltstyp) oder None. Mit Range."""
            try:
                r = dateien({k: v[0] for k, v in parse_qs(u.query).items()})
            except ValueError:
                r = None
            except Exception:      # noqa: BLE001
                r = None
            if not r:
                return self._senden(404, b"")
            p, typ = Path(r[0]), r[1]
            try:
                groesse = p.stat().st_size
                von, bis = 0, groesse - 1
                rng = self.headers.get("Range", "")
                teil = rng.startswith("bytes=")
                if teil:
                    a, _, b = rng[6:].split(",")[0].partition("-")
                    if a:
                        von = int(a)
                        bis = int(b) if b else groesse - 1
                    else:
                        von = max(0, groesse - int(b))
                    bis = min(bis, groesse - 1)
                with open(p, "rb") as f:
                    f.seek(von)
                    daten = f.read(bis - von + 1)
            except (OSError, ValueError):
                return self._senden(404, b"")
            self.send_response(206 if teil else 200)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(daten)))
            self.send_header("Accept-Ranges", "bytes")
            if teil:
                self.send_header("Content-Range", "bytes %d-%d/%d" % (von, bis, groesse))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                self.wfile.write(daten)
            except OSError:
                pass

        def do_POST(self):
            u, ok = self._ok()
            if ok and u.path == "/hochladen":
                return self._hochladen(u)
            if not ok or not u.path.startswith("/api/"):
                return self._senden(403, b"{}")
            name = u.path[5:]
            try:
                n = int(self.headers.get("Content-Length", "0"))
                daten = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            except ValueError:
                return self._senden(400, b"{}")
            if name == "beenden":
                self._senden(200, b"{}")
                return beenden()
            if name not in PASSIV_API:
                _Takt.letzter_ping = time.time()
            if name == "ping":
                return self._senden(200, b'{"ok": true}')
            f = funktionen.get(name)
            if f is None:
                return self._senden(404, b"{}")
            try:
                res = f(daten if isinstance(daten, dict) else {})
                self._senden(200, json.dumps(res, ensure_ascii=False, default=str).encode("utf-8"))
            except ValueError as ex:
                self._senden(400, json.dumps({"fehler": str(ex)}, ensure_ascii=False).encode("utf-8"))
            except Exception as ex:      # noqa: BLE001
                self._senden(500, json.dumps({"fehler": str(ex), "details": traceback.format_exc()},
                                             ensure_ascii=False).encode("utf-8"))

        def _hochladen(self, u):
            """Ins Fenster gezogene Datei (Browser liefert nur den Inhalt, keinen Pfad) in einen Sammelordner schreiben;
            die Seite meldet danach per RPC, was damit geschehen soll (hochlade_ordner(gruppe))."""
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                n = int(self.headers.get("Content-Length", "0"))
                ziel = hochlade_ordner(q.get("gruppe", "")) / _sicherer_dateiname(q.get("name", ""))
                ziel.parent.mkdir(parents=True, exist_ok=True)
                rest = n
                with open(ziel, "wb") as f:
                    while rest > 0:
                        b = self.rfile.read(min(rest, 1 << 20))
                        if not b:
                            break
                        f.write(b)
                        rest -= len(b)
                if rest:
                    raise ValueError("Übertragung abgebrochen")
                self._senden(200, json.dumps({"ok": True, "name": ziel.name}).encode("utf-8"))
            except Exception as ex:      # noqa: BLE001
                self._senden(400, json.dumps({"fehler": str(ex)}, ensure_ascii=False).encode("utf-8"))

    return H


def hochlade_ordner(gruppe: str) -> Path:
    """Sammelordner einer Ablage (eine Gruppe = ein Drop mit mehreren Dateien)."""
    import re as _re
    import tempfile as _tf
    g = _re.sub(r"[^A-Za-z0-9_-]", "", str(gruppe or ""))[:40]
    if not g:
        raise ValueError("Gruppe fehlt")
    return Path(_tf.gettempdir()) / "webshell_hochladen" / g


def _sicherer_dateiname(name: str) -> str:
    import re as _re
    n = _re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", os.path.basename(str(name or "").replace("\\", "/"))).strip().rstrip(". ")
    return n[:150] or "Datei"


def _aktiver_monitor():
    """Arbeitsbereich (links, oben, rechts, unten) des Monitors, auf dem gerade das aktive Fenster (z. B. Directory Opus,
    von dem aus das Script gestartet wurde) liegt; sonst der Monitor unter dem Mauszeiger, sonst None.
    macOS: Bildschirm unter dem Mauszeiger, ohne Menueleiste und Dock."""
    if MAC:
        s = _mac_schirm()
        if not s:
            return None
        x, y, w, h = s["sichtbar"]
        oben = s["h0"] - (y + h)             # Cocoa zaehlt von unten, hier wie unter Windows von oben
        return (int(x), int(oben), int(x + w), int(oben + h)) if w > 300 and h > 300 else None
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class MI(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                        ("dwFlags", wintypes.DWORD)]
        u = ctypes.windll.user32
        u.GetForegroundWindow.restype = wintypes.HWND
        u.MonitorFromWindow.restype = wintypes.HANDLE
        u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        u.MonitorFromPoint.restype = wintypes.HANDLE
        u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MI)]
        hwnd = u.GetForegroundWindow()
        hmon = u.MonitorFromWindow(hwnd, 2) if hwnd else None          # 2 = MONITOR_DEFAULTTONEAREST
        if not hmon:
            pt = wintypes.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            hmon = u.MonitorFromPoint(pt, 2)
        mi = MI()
        mi.cbSize = ctypes.sizeof(MI)
        if hmon and u.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            r = mi.rcWork
            if r.right - r.left > 300 and r.bottom - r.top > 300:
                return (r.left, r.top, r.right, r.bottom)
    except Exception:    # noqa: BLE001
        pass
    return None


# --------------------------------------------------------------------------- #
#  macOS
# --------------------------------------------------------------------------- #
_JXA_SCHIRM = """ObjC.import('AppKit');
var s = $.NSScreen.screens, m = $.NSEvent.mouseLocation, n = 0;
for (var i = 0; i < s.count; i++) { var f = s.objectAtIndex(i).frame;
  if (m.x >= f.origin.x && m.x < f.origin.x + f.size.width && m.y >= f.origin.y && m.y < f.origin.y + f.size.height) { n = i; break; } }
var f = s.objectAtIndex(n).frame, v = s.objectAtIndex(n).visibleFrame;
[n, s.objectAtIndex(0).frame.size.height, f.origin.x, f.origin.y, f.size.width, f.size.height,
 v.origin.x, v.origin.y, v.size.width, v.size.height].join(' ');"""
_SCHIRM = {"zeit": 0.0, "wert": None}
_MAC_HALT = {}
_MAC_TEXTE = {"global.ok": "OK", "global.cancel": "Abbrechen", "global.quit": "Beenden", "global.saveFile": "Speichern",
              "global.quitConfirmation": "Wirklich beenden?", "cocoa.menu.about": "Über", "cocoa.menu.services": "Dienste",
              "cocoa.menu.view": "Darstellung", "cocoa.menu.edit": "Bearbeiten", "cocoa.menu.hide": "Ausblenden",
              "cocoa.menu.hideOthers": "Andere ausblenden", "cocoa.menu.showAll": "Alle einblenden",
              "cocoa.menu.quit": "Beenden", "cocoa.menu.fullscreen": "Vollbild", "cocoa.menu.cut": "Ausschneiden",
              "cocoa.menu.copy": "Kopieren", "cocoa.menu.paste": "Einsetzen", "cocoa.menu.selectAll": "Alles auswählen"}


def _mac_schirm():
    """Bildschirm unter dem Mauszeiger (sonst der Hauptbildschirm): {"nr", "h0", "rahmen", "sichtbar"}. Die Rechtecke
    (x, y, breite, hoehe) stehen in Cocoa-Koordinaten (Ursprung links UNTEN auf dem Hauptbildschirm, h0 = dessen Hoehe);
    "sichtbar" ist die Flaeche ohne Menueleiste und Dock. Mit pyobjc direkt, sonst ueber osascript (bringt macOS mit)."""
    if time.time() - _SCHIRM["zeit"] < 5:
        return _SCHIRM["wert"]
    z = None
    try:
        from AppKit import NSEvent, NSScreen  # type: ignore
        schirme = list(NSScreen.screens())
        m, nr = NSEvent.mouseLocation(), 0
        for i, s in enumerate(schirme):
            f = s.frame()
            if f.origin.x <= m.x < f.origin.x + f.size.width and f.origin.y <= m.y < f.origin.y + f.size.height:
                nr = i
                break
        f, v = schirme[nr].frame(), schirme[nr].visibleFrame()
        z = [nr, schirme[0].frame().size.height, f.origin.x, f.origin.y, f.size.width, f.size.height,
             v.origin.x, v.origin.y, v.size.width, v.size.height]
    except Exception:    # noqa: BLE001
        try:
            r = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", "-e", _JXA_SCHIRM], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, timeout=15)
            z = [float(x) for x in r.stdout.decode("utf-8", "replace").split()]
        except Exception:    # noqa: BLE001
            z = None
    wert = {"nr": int(z[0]), "h0": z[1], "rahmen": tuple(z[2:6]), "sichtbar": tuple(z[6:10])} if z and len(z) == 10 else None
    _SCHIRM.update(zeit=time.time(), wert=wert)
    return wert


def _mac_fensterlage(webview, fx, fy):
    """Lage fuer pywebview: es zaehlt x/y ab der linken oberen Ecke EINES Bildschirms (screen=...), die Geometrie hier
    rechnet dagegen ueber alle Bildschirme hinweg ab der linken oberen Ecke des Hauptbildschirms."""
    s = _mac_schirm()
    if fx is None or not s:
        return {}
    x, y, _w, h = s["rahmen"]
    kw = {"x": int(fx - x), "y": int(fy - (s["h0"] - (y + h)))}
    try:
        schirme = webview.screens() if callable(webview.screens) else webview.screens
        kw["screen"] = schirme[s["nr"]]
    except Exception:    # noqa: BLE001
        pass
    return kw


def _mac_vorbereiten(titel: str, profil: str) -> None:
    """Vor dem Oeffnen des eigenen Fensters: Programmname fuer die Menueleiste (sonst stuende dort "Python"), Symbol fuers
    Dock (nur beim Start aus dem Terminal; ein Start ueber ein .app-Buendel bringt sein Symbol mit), kein App Nap
    (sonst bremst macOS das Laden im Hintergrund, sobald das Fenster verdeckt ist)."""
    try:
        import AppKit  # type: ignore
        import Foundation  # type: ignore
    except Exception:    # noqa: BLE001
        return
    try:
        b = Foundation.NSBundle.mainBundle()
        for info in (b.localizedInfoDictionary(), b.infoDictionary()):
            if info is not None:
                info["CFBundleName"] = titel
    except Exception:    # noqa: BLE001
        pass
    try:
        url = AppKit.NSRunningApplication.currentApplication().bundleURL()
        buendel = os.path.basename(str(url.path()).rstrip("/")) if url is not None else ""
        if profil and not (buendel.endswith(".app") and buendel != "Python.app"):
            daten = symbol_svg(profil).encode("utf-8")
            bild = AppKit.NSImage.alloc().initWithData_(Foundation.NSData.dataWithBytes_length_(daten, len(daten)))
            if bild is not None and bild.isValid():
                AppKit.NSApplication.sharedApplication().setApplicationIconImage_(bild)
    except Exception:    # noqa: BLE001
        pass
    try:
        # NSActivityUserInitiatedAllowingIdleSystemSleep: der Mac darf weiter in den Ruhezustand gehen
        _MAC_HALT["aktiv"] = Foundation.NSProcessInfo.processInfo().beginActivityWithOptions_reason_(0x00EFFFFF, titel)
    except Exception:    # noqa: BLE001
        pass


def _mac_menue(titel: str) -> None:
    """Programm-Menue auf Deutsch: pywebview haengt den Programmnamen immer hinten an ("Ausblenden Trainingsblick")."""
    def arbeit():
        try:
            import AppKit  # type: ignore
            menue = AppKit.NSApplication.sharedApplication().mainMenu().itemAtIndex_(0).submenu()
            texte = {"hide:": "%s ausblenden" % titel, "terminate:": "%s beenden" % titel,
                     "hideOtherApplications:": "Andere ausblenden", "unhideAllApplications:": "Alle einblenden"}
            for i in range(menue.numberOfItems()):
                eintrag = menue.itemAtIndex_(i)
                aktion = eintrag.action()
                aktion = aktion.decode() if isinstance(aktion, bytes) else str(aktion or "")
                if aktion == "orderFrontStandardAboutPanel:":      # zeigte Namen und Version von Python
                    eintrag.setHidden_(True)
                    if i + 1 < menue.numberOfItems() and menue.itemAtIndex_(i + 1).isSeparatorItem():
                        menue.itemAtIndex_(i + 1).setHidden_(True)
                elif aktion in texte:
                    eintrag.setTitle_(texte[aktion])
        except Exception:    # noqa: BLE001
            pass
    try:
        from PyObjCTools import AppHelper  # type: ignore
        AppHelper.callAfter(arbeit)
    except Exception:    # noqa: BLE001
        pass


def _profil_ordner(profil: str) -> str:
    """Eigenes Browser-Profil des App-Fensters (Edge/Chrome): getrennt vom normalen Browser des Nutzers."""
    if MAC:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", profil, "browser")
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), profil, "browser")


def _browser_beenden() -> None:
    """macOS: ein Programm laeuft weiter, wenn sein letztes Fenster zu ist. Den fuer das App-Fenster gestarteten Browser
    deshalb am Ende selbst beenden (er laeuft mit eigenem Profil als eigener Prozess, der normale Browser bleibt offen)."""
    p = _FENSTER_PID.get("prozess")
    if MAC and p is not None and p.poll() is None:
        try:
            p.terminate()
        except OSError:
            pass


def fenster_geometrie(gespeichert, min_w=600, min_h=400, anteil=(0.94, 0.92), standard=(1600, 960)):
    """(breite, hoehe, x, y): Groesse = zuletzt benutzte bzw. Anteil des Monitors. Position: auf dem Monitor des aktiven
    Fensters (Directory Opus); die gemerkte Position gilt nur, wenn sie auf diesem Monitor liegt, sonst mittig dort."""
    g = gespeichert or {}
    mon = _aktiver_monitor()
    if mon is None and os.name == "nt":
        try:
            import ctypes
            mon = (0, 0, ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
        except Exception:    # noqa: BLE001
            mon = None
    gueltig = all(isinstance(g.get(k), (int, float)) for k in ("w", "h", "x", "y")) and g["w"] >= min_w and g["h"] >= min_h
    if mon is None:
        if gueltig:
            return int(g["w"]), int(g["h"]), int(g["x"]), int(g["y"])
        return standard[0], standard[1], None, None
    l, t, r, b = mon
    sw, sh = r - l, b - t
    if gueltig:
        w, h = min(int(g["w"]), sw), min(int(g["h"]), sh)
        cx, cy = g["x"] + g["w"] / 2, g["y"] + g["h"] / 2
        if l <= cx < r and t <= cy < b:
            x = max(l, min(int(g["x"]), r - 100))
            y = max(t, min(int(g["y"]), b - 100))
            return w, h, x, y
    else:
        w, h = min(int(sw * anteil[0]), standard[0]), min(int(sh * anteil[1]), standard[1])
    return w, h, l + (sw - w) // 2, t + max(0, (sh - h) // 2 - 10)


def _eigenes_fenster(titel: str, eigener_prozess: bool = True):
    """Handle des sichtbaren Hauptfensters: eigener Prozess (pywebview) bzw. beliebiger Prozess mit passendem Titel (Edge-App-Fenster)."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    treffer = []
    proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _l):
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if (not eigener_prozess or pid.value == os.getpid()) and u.IsWindowVisible(h) and u.GetParent(h) is None:
            n = u.GetWindowTextLengthW(h)
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, buf, n + 1)
            stil = u.GetWindowLongW(h, -16)
            if stil & 0x00C00000 and (eigener_prozess or buf.value.startswith(titel)):      # WS_CAPTION
                treffer.append((buf.value == titel, h))
        return True
    u.EnumWindows(proto(cb), 0)
    treffer.sort(key=lambda t: not t[0])
    return treffer[0][1] if treffer else None


def _maximieren(titel: str, fenster=None, eigener_prozess: bool = True) -> None:
    """Fenster nach dem Oeffnen wirklich maximieren (Windows-Zustand 'maximiert', Taskleiste bleibt sichtbar)."""
    time.sleep(0.3)
    try:
        if fenster is not None and hasattr(fenster, "maximize"):
            fenster.maximize()
    except Exception:    # noqa: BLE001
        pass
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.IsZoomed.argtypes = [wintypes.HWND]
        u.GetParent.argtypes = [wintypes.HWND]
        u.GetParent.restype = wintypes.HWND
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        for _ in range(80):
            h = _eigenes_fenster(titel, eigener_prozess)
            if h:
                if u.IsZoomed(h):
                    return
                u.ShowWindow(h, 3)                        # 3 = SW_MAXIMIZE
                time.sleep(0.25)
                if u.IsZoomed(h):
                    return
            time.sleep(0.15)
    except Exception:    # noqa: BLE001
        pass


def fenster_oeffnen(url: str, titel: str, geo, profil: str, min_groesse=(700, 450), maximiert: bool = False) -> bool:
    """True, wenn ein eigenes Fenster blockierend geoeffnet wurde (pywebview); sonst wird der Browser gestartet."""
    breite, hoehe, fx, fy = geo
    try:
        import webview  # type: ignore
        kw = {"x": fx, "y": fy} if fx is not None else {}
        if MAC:
            _mac_vorbereiten(titel, profil)
            kw = dict(_mac_fensterlage(webview, fx, fy), localization=_MAC_TEXTE)
        fenster = webview.create_window(titel, url, width=breite, height=hoehe, min_size=min_groesse, **kw)
        FENSTER["webview"] = fenster
        try:
            if MAC:              # "maximiert" heisst hier: das Fenster fuellt schon die freie Flaeche des Bildschirms
                webview.start(lambda: _mac_menue(titel))
            elif maximiert:
                webview.start(lambda: _maximieren(titel, fenster))
            else:
                webview.start()
        finally:
            FENSTER["webview"] = None
        return True
    except Exception:    # noqa: BLE001
        pass
    kandidaten = []
    if os.name == "nt":
        for var in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            b = os.environ.get(var)
            if b:
                kandidaten += [os.path.join(b, r"Microsoft\Edge\Application\msedge.exe"),
                               os.path.join(b, r"Google\Chrome\Application\chrome.exe")]
    elif MAC:
        for ordner in ("/Applications", os.path.expanduser("~/Applications")):
            for name in ("Microsoft Edge", "Google Chrome", "Brave Browser", "Chromium", "Vivaldi"):
                kandidaten.append(os.path.join(ordner, name + ".app", "Contents", "MacOS", name))
    else:
        kandidaten += [shutil.which(x) or "" for x in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser")]
    for k in kandidaten:
        if k and os.path.isfile(k):
            try:
                pfad = _profil_ordner(profil)
                args = [k, f"--app={url}", f"--user-data-dir={pfad}", "--no-first-run", "--no-default-browser-check"]
                if not maximiert or MAC:        # macOS kennt --start-maximized nicht: Groesse = freie Flaeche des Bildschirms
                    args.append(f"--window-size={breite},{hoehe}")
                if fx is not None:
                    args.append(f"--window-position={fx},{fy}")
                if maximiert and not MAC:
                    args.append("--start-maximized")
                prozess = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if MAC else subprocess.Popen(args)
                _FENSTER_PID["pid"], _FENSTER_PID["prozess"] = prozess.pid, prozess
                if maximiert and not MAC:
                    threading.Thread(target=_maximieren, args=(titel, None, False), daemon=True).start()
                return False
            except OSError:
                continue
    webbrowser.open(url)
    return False


def starten(*, funktionen, ui_datei: Path, titel: str, profil: str, geo, argv=None, busy=lambda: 0,
            beim_ende=lambda: None, min_groesse=(700, 450), standard=(1600, 960), anteil=(0.94, 0.92), maximiert: bool = False,
            dateien=None, url_zusatz: str = "", seitentitel: str = "", dauerhaft: bool = False) -> int:
    """Server + Fenster starten und blockieren, bis das Fenster zu ist. Rueckgabe: Exit-Code."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--token", default=None)
    ap.add_argument("--kein-fenster", action="store_true")
    a, _ = ap.parse_known_args(argv)
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    token = a.token or secrets.token_urlsafe(18)
    ende = threading.Event()
    if dauerhaft:
        # Laeuft ohne eigenes Fenster (Hintergrund): ein geschlossenes Fenster beendet ihn nicht; nur der RPC "starter_beenden"
        def stopp(_d):
            threading.Timer(0.3, ende.set).start()
            return {"ok": True}
        funktionen = dict(funktionen, starter_beenden=stopp)

    def beenden():
        if dauerhaft:
            return
        def spaeter():
            time.sleep(2.5)           # Neuladen der Seite soll nicht beenden
            if time.time() - _Takt.letzter_ping > 2 and busy() == 0:
                ende.set()
        threading.Thread(target=spaeter, daemon=True).start()

    _Takt.letzter_ping = time.time()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), _handler(funktionen, token, ui_datei, beenden, profil, dateien, seitentitel))
    url = "http://127.0.0.1:%d/?t=%s%s" % (srv.server_address[1], token, url_zusatz)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        if a.kein_fenster:
            print(url, flush=True)
            try:
                while not ende.is_set():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
            return 0

        def waechter():
            while not ende.is_set():
                time.sleep(2)
                if time.time() - _Takt.letzter_ping > 90 and busy() == 0:
                    ende.set()
        threading.Thread(target=waechter, daemon=True).start()
        fg = fenster_geometrie(geo, min_w=min_groesse[0] - 100, min_h=min_groesse[1] - 100, anteil=anteil, standard=standard)
        if maximiert:
            mon = _aktiver_monitor()
            if mon is not None:                      # Startposition: Arbeitsflaeche des Monitors, auf dem Directory Opus liegt
                fg = (mon[2] - mon[0], mon[3] - mon[1], mon[0], mon[1])
        fenster_melden(titel, profil)
        if not fenster_oeffnen(url, titel, fg, profil, min_groesse, maximiert):
            while not ende.is_set():
                time.sleep(0.5)
        else:                                   # eigenes Fenster zu: laufende Arbeit (z. B. ein Export) darf trotzdem fertig werden
            while busy() > 0:
                time.sleep(1)
        return 0
    finally:
        try:
            fenster_abmelden(profil)
            _browser_beenden()
            beim_ende()
        finally:
            srv.shutdown()
