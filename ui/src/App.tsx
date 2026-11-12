import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { rpc } from "./api";
import { Bestaetigen, Modal } from "./ui";
import { tageBis } from "./events";
import { GDaten, GZ_LEER } from "./erholung";
import { tagesempfehlung } from "./empfehlung";
import { Route } from "./charts";
import { DatumWahl } from "./datum";
import { Einrichtung } from "./einrichtung";
import { Sym, SportSym } from "./symbole";
import { TippHost } from "./tipp";
import { StravaLogo } from "./stravaLogo";
import { MAC } from "./plattform";
import { Studio, StudioStart, TeilenSchnell } from "./studio/Studio";
import { Uebersicht } from "./seiten/uebersicht";
import { Aktivitaeten, Blick } from "./seiten/aktivitaeten";
import { Zeiten, ZeitSport } from "./seiten/zeiten";
import { Koerperdaten, KarteSeite, SportFilter } from "./seiten/koerper";
import { Ctx, Einst, NEBEN_LEER, Seite, Zustand } from "./seiten/ctx";
import {
  Akt, Ev, Extras, KEIN_EXTRAS, istGym, Strecke, streckeAus, Kat, Roh, Zeitraum, aufbereiten, fmtDauer, fmtTag, heuteNr, maxPulsAuto, nf, tempo,
} from "./util";

type Hinweis = { text: string; fehler: boolean } | null;
const SEITEN: [Seite, string, string, string][] = [
  ["uebersicht", "Übersicht", "Heute, Form, Woche, Ziel", "start"],
  ["aktivitaeten", "Aktivitäten", "Woche, Monat, Jahr", "kalender"],
  ["koerper", "Körperdaten", "Schlaf, HRV, Ruhepuls", "puls"],
  ["zeiten", "Zeiten", "Bestzeiten, Entwicklung", "uhr"],
  ["karte", "Karte", "Alle Strecken", "karte"],
];
/** Gespeicherte Ansicht von früher (Woche, Verlauf, Erholung …) auf die neuen Seiten abbilden */
const seiteVon = (a: string): Seite => (SEITEN.some(([k]) => k === a) ? (a as Seite) : a === "erholung" ? "koerper" : a === "karte" ? "karte" : "uebersicht");

function Aktivitaet({ a, onClose, zeige, studio }: { a: Akt; onClose: () => void; zeige: (t: string, f?: boolean) => void; studio: (s: StudioStart) => void }) {
  const [pkt, setPkt] = useState<number[][] | null>(null);
  const [teilen, setTeilen] = useState(false);
  useEffect(() => {
    let weg = false;
    if (!a.r) { setPkt([]); return; }
    rpc<{ punkte: number[][] }>("route", { id: a.id }).then((r) => { if (!weg) setPkt(r.punkte); }).catch(() => { if (!weg) setPkt([]); });
    return () => { weg = true; };
  }, [a.id, a.r]);
  const felder: [string, string][] = [["Distanz", `${nf(a.m / 1000, 2)} km`], ["Dauer", `${fmtDauer(a.t)} h`], ["Tempo", tempo(a)], ["Höhenmeter", `${nf(a.e)} m`]];
  if (a.hr) felder.push(["Ø Puls", `${nf(a.hr)} bpm`]);
  if (a.mhr) felder.push(["Max. Puls", `${nf(a.mhr)} bpm`]);
  if (a.w) felder.push(["Ø Leistung", `${nf(a.w)} W`]);
  if (a.nw) felder.push(["Norm. Leistung", `${nf(a.nw)} W`]);
  if (a.kud) felder.push(["Kudos", String(a.kud)]);
  return (
    <Modal titel={a.n} onClose={onClose}
      foot={<><button className="btn" onClick={() => rpc("strava_oeffnen", { id: a.id }).catch((e) => zeige((e as Error).message, true))}>Auf Strava öffnen</button>{!istGym(a) && <button className="btn" onClick={() => setTeilen(true)}>Teilen …</button>}<button className="btn primary" onClick={onClose}>Schließen</button></>}>
      {teilen && <TeilenSchnell a={a} onClose={() => setTeilen(false)} onStudio={(st) => { onClose(); studio({ ids: [a.id], aktiv: a.id, modus: "einzeln", entwurf: st }); }} />}
      <div className="aktkopf"><SportSym k={a.k} klein />{a.s} · {fmtTag(a.tag, true)} {a.d.slice(11, 16)}{a.tr ? " · Indoor" : ""}</div>
      <div className="aktgrid">
        <div className="stats">{felder.map(([l, v]) => <div key={l}><span className="lbl">{l}</span><b className="mono">{v}</b></div>)}</div>
        <div className="routenbox">{pkt === null ? <div className="leer">Lädt …</div> : <Route punkte={pkt} />}</div>
      </div>
    </Modal>
  );
}

export default function App() {
  const [z, setZ] = useState<Zustand | null>(null);
  const [roh, setRoh] = useState<Roh[]>([]);
  const [einst, setEinst] = useState<Einst | null>(null);
  const [demo, setDemo] = useState(false);
  const [fehler, setFehler] = useState("");
  const [hinweis, setHinweis] = useState<Hinweis>(null);
  const [seite, setSeite] = useState<Seite>("uebersicht");
  const [blick, setBlick] = useState<Blick>({ zoom: "woche", off: 0 });
  const [zeitraum, setZeitraum] = useState<Zeitraum>("12w");
  const [karteSport, setKarteSport] = useState<SportFilter>("alle");
  const [zeitSport, setZeitSport] = useState<ZeitSport>("Run");
  const [offen, setOffen] = useState<Akt | null>(null);
  const [dlg, setDlg] = useState<"einst" | "voll" | "einrichtung" | null>(null);
  const [studio, setStudio] = useState<StudioStart | null>(null);
  const [jetzt, setJetzt] = useState(Date.now() / 1000);
  const geladen = useRef(false);
  const ver = useRef(0);
  const ver2 = useRef(0);
  const karteVer = useRef(-1);
  const einrichtungGezeigt = useRef(false);
  const hauptRef = useRef<HTMLElement>(null);
  const [extras, setExtras] = useState<Extras>(KEIN_EXTRAS);
  const [strecken, setStrecken] = useState<Strecke[]>([]);
  const [gdaten, setGdaten] = useState<GDaten | null>(null);
  const gVer = useRef(-1);
  const [karteGeladen, setKarteGeladen] = useState(false);
  const [dunkel, setDunkel] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  const fensterRef = useRef<{ w: number; h: number; x: number; y: number } | null>(null);
  const hinweisT = useRef<number | undefined>(undefined);

  const zeige = useCallback((text: string, fehler = false) => {
    setHinweis({ text, fehler });
    window.clearTimeout(hinweisT.current);
    hinweisT.current = window.setTimeout(() => setHinweis(null), 7000);
  }, []);
  const aktion = useCallback(async (name: string, body: unknown = {}) => {
    try { const r = await rpc<{ text?: string }>(name, body); if (r?.text) zeige(r.text); } catch (e) { zeige((e as Error).message, true); }
  }, [zeige]);
  const merke = (patch: Record<string, string>) => { rpc("ui_speichern", { patch }).catch(() => undefined); };

  useEffect(() => {
    rpc<{ einst: Einst; demo: boolean }>("start").then((s) => {
      setEinst(s.einst); setDemo(s.demo);
      setZeitraum((["4w", "12w", "jahr", "gesamt"].includes(s.einst.zeitraum) ? s.einst.zeitraum : "12w") as Zeitraum);
      setSeite(seiteVon(s.einst.ansicht));
      if (["Ride", "Run", "Swim"].includes(s.einst.sport)) { setZeitSport(s.einst.sport as ZeitSport); setKarteSport(s.einst.sport as SportFilter); }
      window.setTimeout(() => { geladen.current = true; }, 1500);
    }).catch((e) => setFehler((e as Error).message));
  }, []);
  useEffect(() => {
    let laeuft = false;
    const t = window.setInterval(async () => {
      setJetzt(Date.now() / 1000);
      if (laeuft) return;
      laeuft = true;
      try {
        const zz = await rpc<Zustand>("zustand");
        setZ(zz); setFehler("");
        if (zz.ver2 !== ver2.current) {
          const e = await rpc<{ ver2: number; be: Extras["be"]; wetter: Extras["wetter"] }>("extras");
          ver2.current = e.ver2; setExtras({ be: e.be, wetter: e.wetter });
        }
        if (zz.ver !== ver.current) {
          const d = await rpc<{ ver: number; akt: Roh[] }>("daten");
          ver.current = d.ver; setRoh(d.akt);
        }
      } catch (e) { setFehler((e as Error).message); } finally { laeuft = false; }
    }, 1000);
    return () => window.clearInterval(t);
  }, []);
  useEffect(() => {
    const t = window.setInterval(() => {
      if (!geladen.current) return;
      const g = { w: window.outerWidth, h: window.outerHeight, x: window.screenX, y: window.screenY }, alt = fensterRef.current;
      if (g.w < 600 || g.h < 400) return;
      if (alt && alt.w === g.w && alt.h === g.h && alt.x === g.x && alt.y === g.y) return;
      fensterRef.current = g;
      rpc("ui_speichern", { patch: { fenster: g } }).catch(() => undefined);
    }, 1000);
    return () => window.clearInterval(t);
  }, []);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const h = () => setDunkel(mq.matches);
    mq.addEventListener("change", h);
    return () => mq.removeEventListener("change", h);
  }, []);
  // Erster Start ohne Strava: Einrichtung einmal je Sitzung von selbst zeigen
  useEffect(() => {
    if (!z || einrichtungGezeigt.current || demo || !einst) return;
    einrichtungGezeigt.current = true;
    if (!z.verbunden && z.n === 0) setDlg("einrichtung");
  }, [z, demo, einst]);

  const alle = useMemo(() => aufbereiten(roh), [roh]);
  // Share Studio: ohne Krafttraining
  const teilbar = useMemo(() => alle.filter((a) => !istGym(a)), [alle]);
  useEffect(() => {
    if (seite !== "karte" || !z || karteVer.current === z.ver) return;
    karteVer.current = z.ver;
    rpc<{ routen: [string, string, Kat, string, string][] }>("karte").then((r) => {
      setStrecken(r.routen.map(streckeAus).filter((x): x is Strecke => x !== null)); setKarteGeladen(true);
    }).catch((e) => { karteVer.current = -1; zeige((e as Error).message, true); });
  }, [seite, z, zeige]);
  const gz = z?.garmin ?? GZ_LEER;
  useEffect(() => {
    if (!z?.garmin || !z.garmin.verbunden || gVer.current === z.garmin.ver) return;
    gVer.current = z.garmin.ver;
    rpc<GDaten>("garmin_daten").then(setGdaten).catch((e) => { gVer.current = -1; zeige((e as Error).message, true); });
  }, [z, zeige]);

  const heute = heuteNr();
  const ruhe = einst?.ruhepuls || 50;
  const maxp = einst?.maxpuls || maxPulsAuto(alle);
  const events = useMemo(() => (einst?.events || []).map((e) => ({ ...e, tage: tageBis(e.datum, heute) })).filter((e) => e.tage >= 0)
    .sort((a, b) => (a.haupt === b.haupt ? a.tage - b.tage : a.haupt ? -1 : 1)), [einst, heute]);
  const empf = useMemo(() => tagesempfehlung(gdaten, alle, heute, ruhe, maxp, events[0] ? { tage: events[0].tage, name: events[0].name } : null),
    [gdaten, alle, heute, ruhe, maxp, events]);
  const aufId = useCallback((id: string) => { const a = alle.find((x) => x.id === id); if (a) setOffen(a); }, [alle]);
  const gehe = useCallback((s: Seite) => { setSeite(s); merke({ ansicht: s }); hauptRef.current?.scrollTo({ top: 0 }); }, []);

  const c: Ctx = {
    alle, heute, ruhe, maxp, demo, einst, extras, neben: z?.neben ?? NEBEN_LEER, gdaten, gz, empf: empf ?? null, events,
    auf: setOffen, aufId, aktion, zeige, gehe, einstellungen: () => setDlg("einst"), studio: setStudio,
  };
  const speichern = async (n: Record<string, unknown>) => {
    try { const r = await rpc<{ einst: Einst }>("einstellungen_speichern", n); setEinst(r.einst); return true; } catch (x) { zeige((x as Error).message, true); return false; }
  };

  const alter = z ? Math.max(0, Math.round(jetzt - z.sync.fertig)) : 0;
  const stand = !z ? "lädt …" : z.sync.busy ? z.sync.text : z.sync.fehler ? "Fehler beim Abruf" : z.sync.fertig ? (alter < 90 ? "gerade aktualisiert" : alter < 5400 ? `vor ${Math.round(alter / 60)} min` : alter < 172800 ? `vor ${Math.round(alter / 3600)} h` : `vor ${Math.round(alter / 86400)} Tagen`) : z.verbunden ? "" : "nicht verbunden";
  const gStand = gz.stand > 0 ? new Date(gz.stand * 1000).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";

  return (
    <div className="app">
      {fehler && <div className="verbindung">{fehler}</div>}
      <nav className="nav" aria-label="Bereiche">
        <div className="logo">Trainingsblick<small>{demo ? "Demo-Daten" : `${z ? nf(z.n) : "…"} Einheiten`}</small></div>
        {SEITEN.map(([k, name, unter, sy]) => (
          <button key={k} className="nb" aria-current={seite === k ? "page" : undefined} onClick={() => gehe(k)}>
            <Sym n={sy} /><span>{name}<small>{unter}</small></span>
          </button>
        ))}
        <div className="nav-fuss">
          {z?.update?.neu && (
            <button className="nav-update" onClick={() => void aktion("oeffnen", { ziel: "release" })} data-tipp={MAC ? "Öffnet die Download-Seite. Die Setup-Datei dort ist für Windows; wie das Update auf dem Mac geht, steht im README. Deine Daten bleiben erhalten."
              : "Öffnet die Download-Seite. Die neue Setup-Datei einfach ausführen, deine Daten bleiben erhalten."}>
              <Sym n="download" /><span>Neue Version {z.update.neu}<small>herunterladen …</small></span>
            </button>
          )}
          <div className="nav-stand">
            <span><i className={`stand-pkt${z?.sync.busy ? " laeuft" : z?.sync.fehler ? " fehler" : z?.verbunden ? " ok" : ""}`} />Strava{stand ? ` · ${stand}` : ""}</span>
            {gz.verbunden && <span><i className={`stand-pkt${gz.busy ? " laeuft" : gz.fehler ? " fehler" : " ok"}`} />Garmin{gStand ? ` · ${gStand}` : ""}</span>}
          </div>
          <button className="btn" disabled={!z || z.sync.busy || !z.verbunden || demo} onClick={() => void aktion("aktualisieren")}><Sym n="sync" />{z?.sync.busy ? "Lädt …" : "Aktualisieren"}</button>
          <button className="btn ghost links" onClick={() => setDlg("einst")}><Sym n="zahnrad" />Einstellungen …</button>
          <button className="btn ghost links akzent" onClick={() => setDlg("einrichtung")}><Sym n="sterne" />Einrichtung …</button>
          <StravaLogo className="nav-strava" />
        </div>
      </nav>

      <main className="main" ref={hauptRef}>
        <div className="seite">
          {z?.sync.fehler && z.sync.text && <div className="fehlbox">{z.sync.text}</div>}
          {z && !z.verbunden && !demo && alle.length === 0 && (
            <section className="feld leerfeld">
              <div className="grow"><b>Noch nicht mit Strava verbunden</b><div className="muted">Ohne Strava gibt es noch keine Aktivitäten.</div></div>
              <button className="btn primary" onClick={() => setDlg("einrichtung")}>Einrichtung …</button>
            </section>
          )}
          {seite === "uebersicht" && <Uebersicht c={c} />}
          {seite === "aktivitaeten" && <Aktivitaeten c={c} blick={blick} setBlick={setBlick} />}
          {seite === "koerper" && <Koerperdaten c={c} zeitraum={zeitraum} setZeitraum={(v) => { setZeitraum(v); merke({ zeitraum: v }); }} />}
          {seite === "zeiten" && <Zeiten c={c} sport={zeitSport} setSport={(v) => { setZeitSport(v); merke({ sport: v }); }} />}
          {seite === "karte" && (
            <KarteSeite c={c} strecken={strecken} geladen={karteGeladen} dunkel={dunkel}
              sport={karteSport} setSport={(v) => { setKarteSport(v); merke({ sport: v }); }}
              zeitraum={zeitraum} setZeitraum={(v) => { setZeitraum(v); merke({ zeitraum: v }); }} />
          )}
        </div>
      </main>

      {offen && <Aktivitaet a={offen} onClose={() => setOffen(null)} zeige={zeige} studio={setStudio} />}
      {studio && <Studio akts={teilbar} start={studio} onClose={() => setStudio(null)} />}
      {dlg === "einst" && einst && (
        <EinstDialog e={einst} auto={maxPulsAuto(alle)} onClose={() => setDlg(null)} onVoll={() => setDlg("voll")} demo={demo}
          onSpeichern={async (n) => { if (await speichern(n)) setDlg(null); }} />
      )}
      {dlg === "voll" && (
        <Bestaetigen titel="Alles neu laden?" ja="Neu laden" onJa={() => { setDlg(null); void aktion("aktualisieren", { voll: true }); }} onNein={() => setDlg(null)}>
          Der gesamte Verlauf wird neu von Strava geholt. Gelöschte Einheiten verschwinden dabei auch hier.
        </Bestaetigen>
      )}
      {dlg === "einrichtung" && <Einrichtung z={z} gz={gz} einst={einst} aktion={aktion} speichern={speichern} onClose={() => setDlg(null)} />}
      {hinweis && <div className={"meldung" + (hinweis.fehler ? " bad" : "")} role="status">{hinweis.text}</div>}
      <TippHost />
    </div>
  );
}

function EinstDialog(p: { e: Einst; auto: number; demo: boolean; onClose: () => void; onVoll: () => void; onSpeichern: (n: Record<string, unknown>) => void }) {
  const [ruhe, setRuhe] = useState(String(p.e.ruhepuls));
  const [maxp, setMaxp] = useState(p.e.maxpuls ? String(p.e.maxpuls) : "");
  const [evs, setEvs] = useState<Ev[]>(p.e.events || []);
  const setEv = (i: number, patch: Partial<Ev>) => setEvs(evs.map((e, k) => (k === i ? { ...e, ...patch } : patch.haupt ? { ...e, haupt: false } : e)));
  const [wz, setWz] = useState(p.e.wochenziel ? String(p.e.wochenziel).replace(".", ",") : "");
  const heute = new Date().toISOString().slice(0, 10);
  return (
    <Modal titel="Einstellungen" size="schmal" onClose={p.onClose}
      foot={<>
        <button className="btn ghost" disabled={p.demo} onClick={p.onVoll}>Alles neu laden …</button><span className="grow" />
        <button className="btn" onClick={p.onClose}>Abbrechen</button>
        <button className="btn primary" onClick={() => p.onSpeichern({ ruhepuls: ruhe, maxpuls: maxp || 0, events: evs.filter((e) => e.datum), wochenziel: wz || 0 })}>Speichern</button></>}>
      <div className="formgrid">
        <label>Ruhepuls</label><input type="text" inputMode="numeric" value={ruhe} onChange={(e) => setRuhe(e.target.value)} />
        <label>Maximalpuls</label><input type="text" inputMode="numeric" value={maxp} placeholder={`automatisch (${p.auto})`} onChange={(e) => setMaxp(e.target.value)} />
        <label>Wochenziel (h)</label><input type="text" inputMode="decimal" value={wz} placeholder="keins" onChange={(e) => setWz(e.target.value)} />
      </div>
      <div className="evliste">
        <div className="lbl">Events</div>
        {evs.map((e, i) => (
          <div className="evzeile" key={i}>
            <input type="text" value={e.name} placeholder="Name" onChange={(x) => setEv(i, { name: x.target.value })} />
            <DatumWahl value={e.datum} onChange={(d) => setEv(i, { datum: d })} label="Datum des Events" min={e.datum && e.datum < heute ? e.datum : heute} />
            <button className={`btn sq${e.haupt ? " primary" : ""}`} aria-label="Haupt-Event" data-tipp="Haupt-Event" aria-pressed={e.haupt} onClick={() => setEv(i, { haupt: true })}>★</button>
            <button className="btn sq" aria-label="Entfernen" data-tipp="Entfernen" onClick={() => setEvs(evs.filter((_, k) => k !== i))}>×</button>
          </div>
        ))}
        <button className="btn" onClick={() => setEvs([...evs, { name: "", datum: "", haupt: evs.length === 0, von: heute }])}>+ Event</button>
      </div>
    </Modal>
  );
}
