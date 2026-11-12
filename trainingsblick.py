# -*- coding: utf-8 -*-
"""
Trainingsblick: Auswertung der eigenen Strava-Aktivitaeten (und optional Garmin-Koerperdaten) in einem Fenster,
dazu ein Share Studio fuer Bilder und Videos. Installation und Bedienung: README.md.

Start:          Doppelklick auf "Trainingsblick starten.cmd" (richtet beim ersten Mal alles ein),
                auf dem Mac "Trainingsblick starten.command" (README.md, "Trainingsblick auf dem Mac")
Ohne Fenster:   python trainingsblick.py --kein-fenster [--demo] [--port N] [--token T]   (gibt nur die Adresse aus)
--demo:         erfundene Trainingsdaten, kein Strava-Zugriff (zum Ausprobieren)

Aufbau: Python startet einen lokalen Webserver (nur 127.0.0.1, mit Token) und oeffnet die Oberflaeche (web/index.html, gebaut
aus ui/) als App-Fenster von Edge/Chrome (macOS: eigenes Fenster ueber pywebview). Einstellungen und Zwischenspeicher
liegen in %APPDATA%\\Trainingsblick (macOS: ~/Library/Application Support/Trainingsblick), die Zugangsdaten verschluesselt
in %LOCALAPPDATA%\\Trainingsblick\\geheim (macOS: im Schluesselbund), nie im Programmordner (lib/orte.py).
  lib/strava_api.py            Strava-Anmeldung und Abrufe
  lib/tresor.py                 Zugangsdaten (Strava, Garmin) verschluesselt per Windows-DPAPI bzw. im macOS-Schluesselbund
  lib/trainingsblick_logik.py Aktivitaeten holen und zwischenspeichern, Bestzeiten/Runden/Wetter im Hintergrund, Demo-Daten
  lib/garmin_logik.py           Garmin Connect (Abruf in lib/garmin_helfer.py mit dem Paket garminconnect)
  lib/ablage.py                 Speichern-Dialoge fuer Bilder und Videos (nur Ersatzweg; normal speichert die Seite selbst)
  lib/update.py, lib/version.py Versionsnummer und Hinweis auf neue Releases auf GitHub
  lib/webshell.py               Server, Fenster, Heartbeat
Installer: installer/bauen.ps1 (eigenes Python + Inno Setup), Release per Git-Tag (.github/workflows/release.yml).
Sounds fuer die Videos: Dateien <name>.mp3 in %APPDATA%\\Trainingsblick\\ton (optional); fehlen sie, erzeugt die Seite
die Effekte selbst. Musik gibt es nur als Datei (musik_lofi.mp3, musik_daytona.mp3).
"""
from __future__ import annotations

import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "lib"))
import ablage  # noqa: E402
import garmin_logik as gl  # noqa: E402
import orte  # noqa: E402
import strava_api as sl  # noqa: E402
import trainingsblick_logik as dl  # noqa: E402
import update  # noqa: E402
import version  # noqa: E402
import webshell  # noqa: E402

UI_DATEI = HIER / "web" / "index.html"


class Sitzung:
    def __init__(self, demo=False):
        self.lock = threading.RLock()
        self.demo = demo
        self.cfg = dl.cfg_laden()
        self.speicher = dl.Speicher()
        self.extras = dl.Extras()
        self.strava = None
        self.stopp = threading.Event()
        self.status = {"details": {"fertig": 0, "gesamt": 0, "pause": ""}, "wetter": {"fertig": 0, "gesamt": 0}}
        self.ver2, self._ver2_zeit = 1, 0.0
        if demo:
            self.speicher.akt = {z["id"]: z for z in dl.demo_daten()}
            self.speicher.stand = time.time()
            self.extras = dl.demo_extras(self.speicher.liste())
            runs = [z for z in self.speicher.akt.values() if z["k"] == "Run"]
            self.status = {"details": {"fertig": len(runs), "gesamt": len(runs), "pause": ""},
                           "wetter": {"fertig": len(self.extras.wetter), "gesamt": len(self.extras.wetter)}}
        self.ver = 1
        self.sync = {"busy": False, "text": "", "fehler": False, "fertig": self.speicher.stand}
        self.verb = {"busy": False, "text": ""}
        self.garmin = gl.Garmin(self.cfg, lambda: None, demo)
        self.ablage = ablage.Ablage()
        self.update = {}
        if not demo:
            threading.Thread(target=lambda: setattr(self, "update", update.pruefen()), daemon=True).start()
        if demo:
            self.garmin.pruefen()
        if not demo:
            threading.Thread(target=self.garmin.hintergrund, daemon=True).start()
            self._strava_laden()
            if self.verbunden():
                self.synchronisieren({})
            for f in (dl.details_schleife, dl.wetter_schleife):
                threading.Thread(target=f, args=(self,), daemon=True).start()

    # ---- Strava-Zugang
    def _strava_laden(self):
        self.strava = sl.load_config()

    def verbunden(self):
        return self.demo or bool(self.strava and self.strava.get("refresh_token"))

    def stossen(self):
        """Die Hintergrund-Worker melden neue Zusatzdaten (hoechstens alle 4 Sekunden eine neue Version)."""
        with self.lock:
            if time.time() - self._ver2_zeit > 4:
                self._ver2_zeit = time.time()
                self.ver2 += 1

    # ---- Synchronisierung
    def synchronisieren(self, d):
        if self.demo:
            return {"ok": True}
        with self.lock:
            if self.sync["busy"]:
                return {"ok": True}
            if not self.verbunden():
                raise ValueError("Strava ist noch nicht verbunden")
            self.sync.update(busy=True, text="Lade Aktivitäten …", fehler=False)
        voll = bool(d.get("voll"))
        threading.Thread(target=self._sync, args=(voll,), daemon=True).start()
        return {"ok": True}

    def _sync(self, voll):
        try:
            n = dl.synchronisieren(self.strava, self.speicher, voll=voll, melden=lambda t: self.sync.update(text=t))
            with self.lock:
                self.ver += 1
                self.sync.update(busy=False, fehler=False, fertig=self.speicher.stand,
                                 text=("%d neue oder geänderte Einheiten" % n) if n else "Alles aktuell")
        except Exception as e:      # noqa: BLE001
            with self.lock:
                self.sync.update(busy=False, fehler=True, text="Aktualisieren fehlgeschlagen: %s" % e)

    def verbinden(self, d):
        if self.verb["busy"]:
            raise ValueError("Die Verbindung wird gerade aufgebaut")
        cid, sec = str(d.get("client_id") or "").strip(), str(d.get("client_secret") or "").strip()
        if not self.strava:
            self._strava_laden()
        if cid:
            self.strava["client_id"] = cid
        if sec:
            self.strava["client_secret"] = sec
        self.verb.update(busy=True, text="Browser geöffnet – bitte bei Strava bestätigen …")
        threading.Thread(target=self._verbinden, daemon=True).start()
        return {"ok": True}

    def _verbinden(self):
        try:
            sl.oauth_authorize(self.strava)
            self.verb.update(busy=False, text="")
            self.synchronisieren({})
        except Exception as e:      # noqa: BLE001
            self.verb.update(busy=False, text="Fehler: %s" % e)

    # ---- RPC
    def start(self, _d=None):
        with self.lock:
            return {"fenster": self.cfg.get("fenster"), "einst": self._einst(), "demo": self.demo}

    def _events(self):
        """Events der Einstellungen; ein altes einzelnes Ziel (ziel_name/ziel_datum) wird einmalig uebernommen."""
        c = self.cfg
        ev = c.get("events")
        if not ev and c.get("ziel_datum"):
            ev = [{"name": c.get("ziel_name") or "Wettkampf", "datum": c["ziel_datum"], "haupt": True, "von": time.strftime("%Y-%m-%d")}]
            c["events"] = ev
        return ev or []

    def _einst(self):
        c = self.cfg
        return {"ruhepuls": c.get("ruhepuls") or 50, "maxpuls": c.get("maxpuls") or 0, "events": self._events(),
                "zeitraum": c.get("zeitraum", "12w"), "sport": c.get("sport", "alle"),
                "ansicht": c.get("ansicht", "woche"), "wochenziel": c.get("wochenziel") or 0}

    def zustand(self, _d=None):
        with self.lock:
            return {"ver": self.ver, "ver2": self.ver2, "sync": dict(self.sync), "verb": dict(self.verb), "verbunden": self.verbunden(), "app": bool(self.strava and self.strava.get("client_id") and self.strava.get("client_secret")),
                    "n": len(self.speicher.akt), "jetzt": time.time(), "neben": self.status, "garmin": self.garmin.zustand(),
                    "version": version.VERSION, "update": self.update}

    def daten(self, _d=None):
        with self.lock:
            return {"ver": self.ver, "akt": self.speicher.liste()}

    def extras_holen(self, _d=None):
        with self.lock:
            return {"ver2": self.ver2, "be": dict(self.extras.be), "wetter": dict(self.extras.wetter)}

    def karte(self, d=None):
        """Alle Routen kompakt: [id, Polyline, Sportart, Datum, Name]. virtuell=True nimmt Zwift & Co. mit (fuer das Sammelbild)."""
        virtuell = bool((d or {}).get("virtuell"))
        with self.lock:
            out = []
            for z in self.speicher.liste():
                if self.demo:
                    if z["k"] == "Swim" or z["k"] == "Other":
                        continue
                    poly = dl.polyline_kodieren(dl.demo_route(z["id"]))
                else:
                    # Zwift & Co. liefern Routen auf erfundenen Koordinaten (Suedsee, New York ...) -> nicht auf die Karte;
                    # im Sammelbild steht jede Route fuer sich, da passt die Form der virtuellen Strecke
                    if not virtuell and (z.get("tr") or str(z.get("s", "")).startswith("Virtual")):
                        continue
                    poly = self.speicher.routen.get(z["id"], "")
                if poly:
                    out.append([z["id"], poly, z["k"], z["d"][:10], z["n"]])
            return {"routen": out}

    def route(self, d):
        zid = str(d.get("id", ""))
        if self.demo:
            return {"punkte": dl.demo_route(zid)}
        poly = self.speicher.routen.get(zid, "")
        return {"punkte": dl.polyline_dekodieren(poly) if poly else []}

    OEFFNEN = {"strava_api": "https://www.strava.com/settings/api", "release": "https://github.com/%s/releases/latest" % version.REPO}

    def oeffnen(self, d):
        """Feste Adressen im Browser oeffnen (Einrichtung, Update-Hinweis); beliebige Adressen gibt es nicht."""
        url = self.OEFFNEN.get(str(d.get("ziel") or ""))
        if not url:
            raise ValueError("Unbekanntes Ziel")
        webbrowser.open(url)
        return {"ok": True}

    def strava_oeffnen(self, d):
        zid = "".join(ch for ch in str(d.get("id", "")) if ch.isdigit())
        if not zid:
            raise ValueError("Keine Aktivität gewählt")
        webbrowser.open("https://www.strava.com/activities/" + zid)
        return {"ok": True}

    @staticmethod
    def _events_pruefen(roh):
        if roh is None:
            return None
        if not isinstance(roh, list) or len(roh) > 12:
            raise ValueError("Höchstens 12 Events")
        heute = time.strftime("%Y-%m-%d")
        out = []
        for e in roh:
            datum = str((e or {}).get("datum") or "").strip()
            try:
                time.strptime(datum, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Datum bitte als JJJJ-MM-TT")
            von = str((e or {}).get("von") or "").strip()
            try:
                time.strptime(von, "%Y-%m-%d")
            except ValueError:
                von = heute
            out.append({"name": (str(e.get("name") or "").strip() or "Event")[:60], "datum": datum, "von": min(von, datum),
                        "haupt": bool(e.get("haupt"))})
        if out:
            erste = next((i for i, e in enumerate(out) if e["haupt"]), None)
            if erste is None:
                kuenftig = [i for i, e in enumerate(out) if e["datum"] >= heute] or list(range(len(out)))
                erste = min(kuenftig, key=lambda i: out[i]["datum"])
            for i, e in enumerate(out):
                e["haupt"] = i == erste
        return out

    def einstellungen_speichern(self, d):
        try:
            ruhe, maxp = int(d.get("ruhepuls") or 50), int(d.get("maxpuls") or 0)
        except (TypeError, ValueError):
            raise ValueError("Puls bitte als ganze Zahl eintragen")
        if not 30 <= ruhe <= 90 or (maxp and not 140 <= maxp <= 230):
            raise ValueError("Ruhepuls 30–90, Maximalpuls 140–230 (0 = automatisch)")
        try:
            wz = float(str(d.get("wochenziel") or 0).replace(",", "."))
        except ValueError:
            raise ValueError("Wochenziel bitte als Zahl in Stunden eintragen")
        if not 0 <= wz <= 60:
            raise ValueError("Wochenziel 0–60 Stunden (0 = keins)")
        events = self._events_pruefen(d.get("events"))
        with self.lock:
            self.cfg.update(ruhepuls=ruhe, maxpuls=maxp, wochenziel=wz, ziel_name="", ziel_datum="")
            if events is not None:
                self.cfg["events"] = events
            dl.cfg_speichern(self.cfg)
        return {"ok": True, "einst": self._einst()}

    def ui_speichern(self, d):
        patch = d.get("patch") or {}
        with self.lock:
            for k in ("fenster", "zeitraum", "sport", "ansicht"):
                if k in patch:
                    self.cfg[k] = patch[k]
            dl.cfg_speichern(self.cfg)
        return {"ok": True}

    # ---- Garmin (Abruf laeuft in lib/garmin_helfer.py mit neuem Python)
    def garmin_daten(self, _d=None):
        return self.garmin.daten()

    def garmin_pruefen(self, _d=None):
        threading.Thread(target=self.garmin.pruefen, daemon=True).start()
        return {"ok": True}

    def garmin_installieren(self, _d=None):
        threading.Thread(target=self.garmin.installieren, daemon=True).start()
        return {"ok": True}

    def garmin_anmelden(self, d):
        self.garmin.anmelden(str(d.get("email") or "").strip(), str(d.get("passwort") or ""))
        return {"ok": True}

    def garmin_mfa(self, d):
        self.garmin.mfa_code(d.get("code") or "")
        return {"ok": True}

    def garmin_sync(self, d):
        self.garmin.sync(bool((d or {}).get("voll")))
        return {"ok": True}

    def garmin_trennen(self, _d=None):
        self.garmin.trennen()
        return {"ok": True}

    # ---- Teilen: die Seite erzeugt Bilder/Videos, hier werden sie nur abgelegen
    def teilen_ablegen(self, d):
        """Datei, die die Seite ueber /hochladen geschickt hat, per Speichern-Dialog ablegen."""
        quelle = webshell.hochlade_ordner(str(d.get("gruppe") or "")) / str(d.get("name") or "")
        return self.ablage.ablegen(quelle, str(d.get("name") or "Teilen.png"))

    def runden(self, d):
        """Runden (Laps) einer Einheit fuers Studio. Fehlen sie noch und holen=True, gleich einzeln bei Strava abrufen."""
        zid = str(d.get("id", ""))
        with self.lock:
            z = self.speicher.akt.get(zid)
            lp = self.extras.lp.get(zid)
        if self.demo:
            return {"lp": dl.demo_runden(z)}
        if lp is not None or not z or z["k"] not in dl.RUNDEN_SPORT or not d.get("holen") or not (self.strava and self.strava.get("refresh_token")):
            return {"lp": lp or []}
        try:
            detail = sl.api_get(self.strava, "/activities/%s" % zid)
        except Exception:       # noqa: BLE001  ohne Runden geht es auch (dann nur die Route)
            return {"lp": []}
        with self.lock:
            self.extras.anzahl += 1
            dl.detail_merken(self.extras, z, detail)
            self.extras.speichern()
            return {"lp": self.extras.lp.get(zid) or []}

    def teilen_ablegen_ordner(self, d):
        """Mehrere ueber /hochladen geschickte Bilder (alle einer Gruppe) in einen gewaehlten Ordner legen."""
        ordner = webshell.hochlade_ordner(str(d.get("gruppe") or ""))
        namen = [str(n) for n in (d.get("namen") or [])]
        return self.ablage.ablegen_ordner([ordner / n for n in namen])

    def sammel_design(self, _d=None):
        with self.lock:
            return {"design": self.cfg.get("sammel")}

    # ---- Studio, Einzelbild: Standard-Design und eigene Vorlagen
    def einzel_design(self, _d=None):
        with self.lock:
            return {"design": self.cfg.get("einzeln")}

    def einzel_speichern(self, d):
        if not isinstance(d.get("design"), dict):
            raise ValueError("Kein Design")
        with self.lock:
            self.cfg["einzeln"] = d["design"]
            dl.cfg_speichern(self.cfg)
        return {"ok": True}

    def vorlagen(self, _d=None):
        """Eigene Vorlagen (Presets aus einem anderen Programm gibt es hier nicht)."""
        with self.lock:
            return {"eigen": dict(self.cfg.get("vorlagen") or {}), "presets": []}

    def vorlage_speichern(self, d):
        name = str(d.get("name") or "").strip()
        if not name or not isinstance(d.get("design"), dict):
            raise ValueError("Name und Design fehlen")
        with self.lock:
            v = dict(self.cfg.get("vorlagen") or {})
            v[name] = d["design"]
            self.cfg["vorlagen"] = v
            dl.cfg_speichern(self.cfg)
        return {"ok": True}

    def vorlage_loeschen(self, d):
        with self.lock:
            v = dict(self.cfg.get("vorlagen") or {})
            v.pop(str(d.get("name") or ""), None)
            self.cfg["vorlagen"] = v
            dl.cfg_speichern(self.cfg)
        return {"ok": True}

    def sammel_speichern(self, d):
        if not isinstance(d.get("design"), dict):
            raise ValueError("Kein Design")
        with self.lock:
            self.cfg["sammel"] = d["design"]
            dl.cfg_speichern(self.cfg)
        return {"ok": True}

    def ton_ordner(self):
        """Eigene Sounds fuer die Videos (z. B. aus der eigenen Sammlung); ohne Ordner erzeugt die Seite die Effekte selbst."""
        return Path(self.cfg.get("ton_ordner") or orte.TON)

    def ton_liste(self, _d=None):
        """Welche Sounds als Datei da sind (die anderen erzeugt die Seite selbst)."""
        o = self.ton_ordner()
        return {"namen": sorted(p.stem for p in o.glob("*.mp3")) if o.is_dir() else []}

    def datei(self, q):
        """/datei?art=ton&name=woosh -> <Ton-Ordner>/woosh.mp3"""
        import re
        name = str(q.get("name") or "")
        if q.get("art") != "ton" or not re.fullmatch(r"[a-z_]{2,30}", name):
            return None
        p = self.ton_ordner() / (name + ".mp3")
        return (p, "audio/mpeg") if p.is_file() else None

    def teilen_ordner(self, d):
        self.ablage.ordner_zeigen(d.get("pfad") or None)
        return {"ok": True}

    def ende(self):
        self.stopp.set()
        self.garmin.beenden()
        with self.lock:
            dl.cfg_speichern(self.cfg)
            if not self.demo:
                self.extras.speichern()


def aufrufe(s):
    return {"start": s.start, "zustand": s.zustand, "daten": s.daten, "extras": s.extras_holen, "karte": s.karte, "aktualisieren": s.synchronisieren, "verbinden": s.verbinden,
            "route": s.route, "strava_oeffnen": s.strava_oeffnen, "oeffnen": s.oeffnen, "einstellungen_speichern": s.einstellungen_speichern,
            "ui_speichern": s.ui_speichern, "garmin_daten": s.garmin_daten, "garmin_pruefen": s.garmin_pruefen,
            "garmin_installieren": s.garmin_installieren, "garmin_anmelden": s.garmin_anmelden, "garmin_mfa": s.garmin_mfa,
            "garmin_sync": s.garmin_sync, "garmin_trennen": s.garmin_trennen,
            "teilen_ablegen": s.teilen_ablegen,
            "teilen_ablegen_ordner": s.teilen_ablegen_ordner, "runden": s.runden, "einzel_design": s.einzel_design, "einzel_speichern": s.einzel_speichern,
            "vorlagen": s.vorlagen, "vorlage_speichern": s.vorlage_speichern, "vorlage_loeschen": s.vorlage_loeschen,
            "sammel_design": s.sammel_design, "sammel_speichern": s.sammel_speichern, "ton_liste": s.ton_liste, "teilen_ordner": s.teilen_ordner}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    s = Sitzung(demo="--demo" in args)
    return webshell.starten(funktionen=aufrufe(s), ui_datei=UI_DATEI, titel="Trainingsblick", profil="Trainingsblick",
                            geo=s.cfg.get("fenster"), argv=args, beim_ende=s.ende, busy=lambda: 1 if s.sync["busy"] else 0,
                            min_groesse=(960, 620), standard=(1560, 960), anteil=(0.94, 0.92), maximiert=True, dateien=s.datei)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        tb = traceback.format_exc()
        try:
            pfad = orte.LOGS
            pfad.mkdir(parents=True, exist_ok=True)
            (pfad / ("trainingsblick_fehler_%s.txt" % time.strftime("%Y%m%d_%H%M%S"))).write_text(tb, encoding="utf-8")
        except OSError:
            pass
        raise
