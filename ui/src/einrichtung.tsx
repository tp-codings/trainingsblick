/* Einrichtung beim ersten Start: Strava verbinden, Garmin (optional), Ziel (optional), erster Abruf */
import { useEffect, useState } from "react";
import { GarminVerbinden, GZ } from "./erholung";
import { DatumWahl } from "./datum";
import { Sym, SymFeld } from "./symbole";
import { nf, Ev } from "./util";
import { dateiWaehlen } from "./speichern";
import { StravaLogo } from "./stravaLogo";
import { MAC } from "./plattform";
import type { Aktion, Einst, Zustand } from "./seiten/ctx";

const SCHRITTE: [string, string, string][] = [["kette", "Strava", "Aktivitäten"], ["uhrband", "Garmin", "optional"], ["flagge", "Ziel", "optional"], ["haken", "Fertig", "erster Abruf"]];
const CID_OK = /^\d{3,12}$/;
const SEC_OK = /^[0-9a-f]{40}$/i;
/** Felder des (englischen) Strava-Formulars: Feldname, was hinein soll, Wert zum Kopieren, wichtig */
const FELDER: [string, string, string, boolean][] = [
  ["Application Name", "Mein Dashboard", "Mein Dashboard", false],
  ["Category", "„Data Importer“ auswählen", "", false],
  ["Club", "leer lassen", "", false],
  ["Website", "http://localhost", "http://localhost", false],
  ["Application Description", "leer lassen", "", false],
  ["Authorization Callback Domain", "localhost", "localhost", true],
];

/** Bild für die Strava-App (Strava verlangt manchmal eins): das Programmsymbol, wie installer/symbol.py */
function appBild(): Promise<Blob> {
  const n = 512, c = document.createElement("canvas");
  c.width = c.height = n;
  const g = c.getContext("2d")!;
  const v = g.createLinearGradient(0, 0, 0, n);
  v.addColorStop(0, "#22c3b4"); v.addColorStop(1, "#1f5fd6");
  g.fillStyle = v;
  g.beginPath(); g.roundRect(0, 0, n, n, n * 0.22); g.fill();
  g.strokeStyle = "#fff"; g.lineWidth = n * 0.095; g.lineCap = "round"; g.lineJoin = "round";
  g.beginPath();
  [[0.2, 0.68], [0.37, 0.44], [0.5, 0.57], [0.65, 0.31], [0.81, 0.63]].forEach(([x, y], k) => (k ? g.lineTo(x * n, y * n) : g.moveTo(x * n, y * n)));
  g.stroke();
  return new Promise((ok, fehl) => c.toBlob((b) => (b ? ok(b) : fehl(new Error("Bild ließ sich nicht erstellen"))), "image/png"));
}

/** Schritt für Schritt zur eigenen Strava-API-App, mit Kopier-Knöpfen und Prüfung der eingefügten Werte */
function StravaAnleitung({ cid, setCid, sec, setSec, aktion }: { cid: string; setCid: (v: string) => void; sec: string; setSec: (v: string) => void; aktion: Aktion }) {
  const [kopiert, setKopiert] = useState("");
  const [bild, setBild] = useState("");
  const kopieren = async (wert: string) => {
    try { await navigator.clipboard.writeText(wert); } catch {
      // Zwischenablage gesperrt: alter Weg über ein verstecktes Textfeld
      const t = document.createElement("textarea");
      t.value = wert; t.style.position = "fixed"; t.style.opacity = "0";
      document.body.appendChild(t); t.select();
      const ok = document.execCommand("copy");
      t.remove();
      if (!ok) { setKopiert("!" + wert); return; }
    }
    setKopiert(wert);
    window.setTimeout(() => setKopiert((k) => (k === wert ? "" : k)), 1600);
  };
  const bildSpeichern = async () => {
    try {
      const ziel = await dateiWaehlen("Trainingsblick.png");
      const g = ziel && await ziel.schreiben(await appBild());
      if (g) setBild("Bild gespeichert. Bei Strava auf das Bildfeld klicken und diese Datei wählen.");
    } catch (e) { setBild((e as Error).message); }
  };
  const c = cid.trim(), s = sec.trim();
  return (
    <div className="ob-anleitung">
      <div className="ob-karte">
        <span className="ob-nr">1</span>
        <div className="grow"><b>Strava-Seite für Entwickler öffnen</b><small>Dort ggf. anmelden. Die Seite ist auf Englisch, die Felder stehen hier übersetzt.</small></div>
        <button className="btn" onClick={() => void aktion("oeffnen", { ziel: "strava_api" })}><Sym n="extern" />Strava öffnen</button>
      </div>
      <div className="ob-karte">
        <span className="ob-nr">2</span>
        <div className="grow">
          <b>Formular „My API Application“ ausfüllen</b>
          <table className="ob-felder"><colgroup><col className="feld" /><col /><col className="knopf" /></colgroup><tbody>
            {FELDER.map(([feld, inhalt, wert, wichtig]) => (
              <tr key={feld} className={wichtig ? "wichtig" : ""}>
                <td>{feld}</td>
                <td>{wert ? <code>{inhalt}</code> : <span className="muted">{inhalt}</span>}{wichtig && <small>genau so, ohne http und ohne Schrägstrich</small>}</td>
                <td>{wert && (kopiert === "!" + wert
                  ? <small>bitte markieren und mit {MAC ? "⌘C" : "Strg+C"} kopieren</small>
                  : <button className="btn small" onClick={() => void kopieren(wert)}><Sym n={kopiert === wert ? "haken" : "kopieren"} />{kopiert === wert ? "Kopiert" : "Kopieren"}</button>)}</td>
              </tr>
            ))}
          </tbody></table>
          <small>Dann den Haken bei den Bedingungen setzen und auf <b>„Create“</b> klicken. Fragt Strava nach einem Bild für die App:{" "}
            <button className="btn-link" onClick={() => void bildSpeichern()}>passendes Bild speichern …</button></small>
          {bild && <small className="ob-hinweis">{bild}</small>}
        </div>
      </div>
      <div className="ob-karte">
        <span className="ob-nr">3</span>
        <div className="grow">
          <b>Client ID und Client Secret hier einfügen</b>
          <small>Sie stehen danach auf derselben Seite. Beim Client Secret erst auf „Show“ klicken.</small>
          <div className="ob-form">
            <label>Client ID<input type="text" inputMode="numeric" value={cid} placeholder="z. B. 123456" onChange={(e) => setCid(e.target.value)} />
              {c && !CID_OK.test(c) && <small className="bad">Die Client ID ist nur eine Zahl.</small>}</label>
            <label>Client Secret<input type="password" value={sec} placeholder="40 Zeichen" onChange={(e) => setSec(e.target.value)} />
              {s && !SEC_OK.test(s) && <small className="bad">{s.length < 40 ? `Erst ${s.length} von 40 Zeichen. Auf „Show“ geklickt und alles kopiert?` : "Das sieht nicht nach einem Client Secret aus (40 Zeichen aus 0–9 und a–f)."}</small>}</label>
          </div>
        </div>
      </div>
    </div>
  );
}

const heuteIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

export function Einrichtung({ z, gz, einst, aktion, speichern, onClose }: {
  z: Zustand | null; gz: GZ; einst: Einst | null; aktion: Aktion;
  speichern: (patch: Record<string, unknown>) => Promise<boolean>; onClose: () => void;
}) {
  const [i, setI] = useState(0);
  const [cid, setCid] = useState(""), [sec, setSec] = useState("");
  const heute = heuteIso();
  const haupt = (einst?.events || []).find((e) => e.haupt && e.datum >= heute) ?? (einst?.events || []).find((e) => e.datum >= heute);
  const [evName, setEvName] = useState(haupt?.name ?? "");
  const [evDatum, setEvDatum] = useState(haupt?.datum ?? "");
  const [wz, setWz] = useState(einst?.wochenziel ? String(einst.wochenziel).replace(".", ",") : "");
  const verbunden = !!z?.verbunden;
  const [andereApp, setAndereApp] = useState(false);
  const eingegeben = CID_OK.test(cid.trim()) && SEC_OK.test(sec.trim());

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  const zielSpeichern = async () => {
    if (evName.trim() && !evDatum) return;
    const andere = (einst?.events || []).filter((e) => e !== haupt);
    const events: Ev[] = evName.trim() && evDatum
      ? [{ name: evName.trim(), datum: evDatum, haupt: true, von: haupt?.von || heute }, ...andere.map((e) => ({ ...e, haupt: false }))]
      : einst?.events || [];
    const ok = await speichern({ ruhepuls: einst?.ruhepuls || 50, maxpuls: einst?.maxpuls || 0, events, wochenziel: wz || 0 });
    if (ok) setI(3);
  };

  const zurueck = i > 0 ? <button className="btn" onClick={() => setI(i - 1)}>Zurück</button> : null;
  let inhalt: JSX.Element;
  if (i === 0) {
    inhalt = (
      <>
        <h2><SymFeld n="kette" farbe="#fc4c02" />Mit Strava verbinden</h2>
        {verbunden ? (
          <>
            <div className="ob-status"><Sym n="haken" />Strava ist verbunden · {nf(z?.n ?? 0)} Einheiten</div>
            <div className="ob-fuss"><StravaLogo className="ob-strava" /><span className="grow" /><button className="btn primary" onClick={() => setI(1)}>Weiter</button></div>
          </>
        ) : (
          <>
            {z?.app && !andereApp ? (
              // Client ID und Secret liegen schon im Tresor (z. B. übernommen): nur noch im Browser bestätigen
              <div className="ob-karte">
                <Sym n="haken" />
                <div className="grow">
                  <b>Deine Strava-App ist schon eingetragen</b>
                  <small>Klick auf „Mit Strava verbinden …“ und bestätige im Browser. {" "}
                    <button className="btn-link" onClick={() => setAndereApp(true)}>Andere App eintragen …</button></small>
                </div>
              </div>
            ) : (
              <>
                <p>Strava gibt deine Aktivitäten nur an Programme heraus, die du selbst bei Strava anmeldest. Das ist kostenlos und dauert etwa drei Minuten.</p>
                <StravaAnleitung cid={cid} setCid={setCid} sec={sec} setSec={setSec} aktion={aktion} />
              </>
            )}
            {z?.verb.text && <div className={z.verb.text.startsWith("Fehler") ? "fehlbox" : "muted"}>{z.verb.text}</div>}
            <div className="ob-sicher"><Sym n="haken" />Client ID und Secret bleiben verschlüsselt auf deinem {MAC ? "Mac" : "PC"}.</div>
            <div className="ob-fuss">
              <StravaLogo className="ob-strava" />
              <span className="grow" />
              <button className="btn" onClick={() => setI(1)}>Später</button>
              <button className="btn primary" disabled={!z || z.verb.busy || !(eingegeben || (z.app && !andereApp))}
                onClick={() => void aktion("verbinden", eingegeben ? { client_id: cid.trim(), client_secret: sec.trim() } : {})}>
                {z?.verb.busy ? "Warte auf Strava …" : "Mit Strava verbinden …"}
              </button>
            </div>
          </>
        )}
      </>
    );
  } else if (i === 1) {
    inhalt = (
      <>
        <h2><SymFeld n="uhrband" />Garmin verbinden</h2>
        <p>Für Schlaf, HRV, Ruhepuls, Body Battery und die Bereitschaft am Morgen. Ohne Garmin fehlen nur die Körperdaten.</p>
        {gz.verbunden && !gz.anmelden ? <div className="ob-status"><Sym n="haken" />Garmin ist verbunden</div> : <GarminVerbinden gz={gz} aktion={aktion} ohneRahmen />}
        <div className="ob-sicher"><Sym n="haken" />Das Passwort wird nicht gespeichert, nur der Zugang von Garmin.</div>
        <div className="ob-fuss">
          {zurueck}<span className="grow" />
          {gz.verbunden && !gz.anmelden ? <button className="btn primary" onClick={() => setI(2)}>Weiter</button> : <button className="btn" onClick={() => setI(2)}>Überspringen</button>}
        </div>
      </>
    );
  } else if (i === 2) {
    inhalt = (
      <>
        <h2><SymFeld n="flagge" />Trainierst du auf ein Ziel hin?</h2>
        <p>Dann zeigt die Übersicht den Countdown bis zum Renntag.</p>
        <div className="ob-form">
          <label className="ganz">Event<input type="text" value={evName} placeholder="z. B. Halbmarathon Freiburg" onChange={(e) => setEvName(e.target.value)} /></label>
          <label>Datum<DatumWahl value={evDatum} onChange={setEvDatum} label="Datum des Events" min={heute} /></label>
          <label>Wochenziel in Stunden<input type="text" inputMode="decimal" value={wz} placeholder="keins" onChange={(e) => setWz(e.target.value)} /></label>
        </div>
        {evName.trim() && !evDatum && <div className="muted">Bitte noch das Datum wählen.</div>}
        <div className="ob-fuss">
          {zurueck}<span className="grow" />
          <button className="btn" onClick={() => setI(3)}>Kein Ziel</button>
          <button className="btn primary" disabled={!!evName.trim() && !evDatum} onClick={() => void zielSpeichern()}>Weiter</button>
        </div>
      </>
    );
  } else {
    const syncAn = !!z?.sync.busy, gAn = gz.busy && gz.art === "sync";
    inhalt = (
      <>
        <h2><SymFeld n="haken" farbe="var(--ok)" />Alles bereit</h2>
        <p>{verbunden ? "Deine Aktivitäten werden geladen. Was schon da ist, siehst du sofort, ältere Einheiten kommen im Hintergrund dazu." : "Strava ist noch nicht verbunden. Das geht jederzeit über „Einrichtung …“ in der Seitenleiste."}</p>
        <div className="ob-fortschritt">
          <div className="ob-zeile"><SymFeld n="kette" farbe="#fc4c02" klein /><span className="grow">Aktivitäten von Strava</span><b className="mono">{!verbunden ? "nicht verbunden" : syncAn ? z!.sync.text : `${nf(z!.n)} Einheiten`}</b></div>
          {verbunden && <div className={`balken${syncAn ? " laeuft" : ""}`}><i style={{ width: syncAn ? "40%" : "100%", background: syncAn ? "var(--accent)" : "var(--ok)" }} /></div>}
          <div className="ob-zeile"><SymFeld n="uhrband" klein /><span className="grow">Körperdaten von Garmin</span><b className="mono">{gAn ? `${gz.fertig} von ${gz.gesamt}` : gz.verbunden ? "fertig" : "nicht verbunden"}</b></div>
          {gz.verbunden && <div className="balken"><i style={{ width: gAn && gz.gesamt ? `${(gz.fertig / gz.gesamt) * 100}%` : "100%", background: gAn ? "var(--accent)" : "var(--ok)" }} /></div>}
        </div>
        <div className="ob-sicher">Alles lässt sich später unter Einstellungen ändern.</div>
        <div className="ob-fuss">{zurueck}<span className="grow" /><button className="btn primary" onClick={onClose}>Zum Dashboard</button></div>
      </>
    );
  }
  return (
    <div className="ob-hinter" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="ob" role="dialog" aria-label="Einrichtung">
        <aside className="ob-seite">
          <div className="logo">Trainingsblick<small>Einrichtung</small></div>
          {SCHRITTE.map(([sy, t, u], k) => {
            // Haken nur, wenn es wirklich erledigt ist (übersprungenes Strava/Garmin bleibt ohne)
            const erledigt = k === 0 ? verbunden : k === 1 ? gz.verbunden && !gz.anmelden : k < i;
            return (
              <button key={t} className={`ob-schritt${k === i ? " jetzt" : erledigt ? " fertig" : ""}`} onClick={() => setI(k)}>
                <SymFeld n={erledigt && k !== i ? "haken" : sy} /><span>{t}<small>{u}</small></span>
              </button>
            );
          })}
        </aside>
        <div className="ob-inhalt">{inhalt}</div>
      </div>
    </div>
  );
}
