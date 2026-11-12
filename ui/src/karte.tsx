import { useEffect, useRef, useState } from "react";
import { Kat, Strecke, fmtTag } from "./util";

type Ansicht = { cx: number; cy: number; s: number };       // Mittelpunkt (Welt 0..1), Pixel je Welteinheit
const TILE = 256;
const KAT_FARBE: Record<Kat, string> = { Ride: "--c-ride", Run: "--c-run", Swim: "--c-swim", Other: "--c-other" };

/** Einpassen: standardmaessig auf die Routen rund um den Schwerpunkt (naechste 85 %), mit `alle` auf wirklich alle. */
function einpassen(st: Strecke[], b: number, h: number, alle: boolean): Ansicht {
  if (!st.length) return { cx: 0.53, cy: 0.33, s: TILE * 2 ** 8 };
  let sel = st;
  if (!alle && st.length > 6) {
    const mitte = (r: Strecke) => [(r.bb[0] + r.bb[2]) / 2, (r.bb[1] + r.bb[3]) / 2];
    const med = (w: number[]) => { const o = w.slice().sort((p, q) => p - q); return o[Math.floor(o.length / 2)]; };
    const mx = med(st.map((r) => mitte(r)[0])), my = med(st.map((r) => mitte(r)[1]));
    const dist = (r: Strecke) => { const m = mitte(r); return Math.hypot(m[0] - mx, m[1] - my); };
    sel = st.slice().sort((p, q) => dist(p) - dist(q)).slice(0, Math.ceil(st.length * 0.85));
  }
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const r of sel) { x0 = Math.min(x0, r.bb[0]); y0 = Math.min(y0, r.bb[1]); x1 = Math.max(x1, r.bb[2]); y1 = Math.max(y1, r.bb[3]); }
  const bw = Math.max(x1 - x0, 1e-5) * 1.12, bh = Math.max(y1 - y0, 1e-5) * 1.12;
  return { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, s: Math.min(TILE * 2 ** 19, Math.min(b / bw, h / bh)) };
}

const FILTER_DUNKEL = "invert(1) hue-rotate(180deg) brightness(0.75) contrast(0.85) saturate(0.6)";
// WebKit (Safari, das Fenster der Mac-App) kennt filter auf dem Canvas nicht: dort bleibt die Zuweisung ohne Wirkung
const KANN_FILTER = typeof CanvasRenderingContext2D !== "undefined" && "filter" in CanvasRenderingContext2D.prototype;

/** Kartenkachel fuer das dunkle Design ohne Canvas-Filter: dasselbe Ergebnis wie FILTER_DUNKEL, aus Mischmodi gebaut. */
function kachelDunkel(g: CanvasRenderingContext2D, im: HTMLImageElement, x: number, y: number, w: number, h: number) {
  g.drawImage(im, x, y, w, h);
  g.globalCompositeOperation = "difference"; g.fillStyle = "#fff"; g.fillRect(x, y, w, h);      // invert(1)
  g.globalCompositeOperation = "color"; g.drawImage(im, x, y, w, h);                            // hue-rotate(180deg): Farbton wie vorher
  g.globalCompositeOperation = "saturation"; g.globalAlpha = 0.4; g.fillStyle = "#808080"; g.fillRect(x, y, w, h);   // saturate(0.6)
  g.globalCompositeOperation = "source-over";
  g.globalAlpha = 0.25; g.fillStyle = "#000"; g.fillRect(x, y, w, h);                           // brightness(0.75)
  g.globalAlpha = 0.15; g.fillStyle = "#808080"; g.fillRect(x, y, w, h);                        // contrast(0.85)
  g.globalAlpha = 1;
}

export function RoutenKarte({ strecken, kacheln, dunkel, reset, auf, fokus }: { strecken: Strecke[]; kacheln: boolean; dunkel: boolean; reset: number; auf: (id: string) => void; fokus: Strecke | null }) {
  const wrap = useRef<HTMLDivElement>(null);
  const cv = useRef<HTMLCanvasElement>(null);
  const ansicht = useRef<Ansicht>({ cx: 0.5, cy: 0.5, s: TILE * 2 ** 8 });
  const groesse = useRef({ b: 800, h: 500, dpr: 1 });
  const bilder = useRef(new Map<string, HTMLImageElement | "fehler">());
  const treffer = useRef<string | null>(null);
  const raf = useRef(0);
  const [tip, setTip] = useState<{ x: number; y: number; r: Strecke } | null>(null);
  const props = useRef({ strecken, kacheln, dunkel, fokus });
  props.current = { strecken, kacheln, dunkel, fokus };

  const zeichnen = () => {
    const c = cv.current;
    if (!c) return;
    const g = c.getContext("2d");
    if (!g) return;
    const { b, h, dpr } = groesse.current, { cx, cy, s } = ansicht.current, p = props.current;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const css = getComputedStyle(document.documentElement);
    g.fillStyle = css.getPropertyValue("--surface2").trim() || "#eee";
    g.fillRect(0, 0, b, h);
    if (p.kacheln) {
      const tz = Math.max(0, Math.min(18, Math.round(Math.log2(s / TILE))));
      const n = 2 ** tz, ts = s / n;
      const x0 = Math.floor((cx - b / 2 / s) * n), x1 = Math.floor((cx + b / 2 / s) * n), y0 = Math.floor((cy - h / 2 / s) * n), y1 = Math.floor((cy + h / 2 / s) * n);
      if ((x1 - x0 + 1) * (y1 - y0 + 1) <= 120) {
        for (let tx = x0; tx <= x1; tx++) for (let ty = y0; ty <= y1; ty++) {
          if (ty < 0 || ty >= n) continue;
          const wx = ((tx % n) + n) % n, key = `${tz}/${wx}/${ty}`;
          let im = bilder.current.get(key);
          if (!im) {
            const i = new Image();
            i.onload = () => { schedule(); };
            i.onerror = () => { bilder.current.set(key, "fehler"); };
            i.src = `https://tile.openstreetmap.org/${tz}/${wx}/${ty}.png`;
            bilder.current.set(key, i);
            im = i;
          }
          if (im !== "fehler" && im.complete && im.naturalWidth > 0) {
            if (p.dunkel && !KANN_FILTER) {
              // auf ganze Bildpunkte gelegt: die Kacheln duerfen sich hier nicht ueberlappen (doppelt umgekehrt = wieder hell)
              const kante = (t: number, m: number) => Math.round(((t / n - m) * s) * dpr + (m === cx ? b : h) / 2 * dpr) / dpr;
              const x = kante(tx, cx), y = kante(ty, cy);
              kachelDunkel(g, im, x, y, kante(tx + 1, cx) - x, kante(ty + 1, cy) - y);
            } else {
              g.filter = p.dunkel ? FILTER_DUNKEL : "none";
              g.drawImage(im, (tx / n - cx) * s + b / 2, (ty / n - cy) * s + h / 2, ts + 0.6, ts + 0.6);
              g.filter = "none";
            }
          }
        }
      }
    }
    // Routen: viele halbtransparente Linien ergeben die Haeufigkeit (dunkel: additiv, hell: ueberlagernd)
    g.lineJoin = "round"; g.lineCap = "round";
    g.globalCompositeOperation = p.dunkel ? "lighter" : "source-over";
    const farben: Record<string, string> = {};
    (Object.keys(KAT_FARBE) as Kat[]).forEach((k) => { farben[k] = css.getPropertyValue(KAT_FARBE[k]).trim(); });
    const vx0 = cx - b / 2 / s, vx1 = cx + b / 2 / s, vy0 = cy - h / 2 / s, vy1 = cy + h / 2 / s;
    const liste = p.fokus && !p.strecken.some((r) => r.id === p.fokus!.id) ? [...p.strecken, p.fokus] : p.strecken;
    for (const pass of [0, 1]) {
      for (const r of liste) {
        const aktiv = r.id === treffer.current || r === p.fokus || r.id === p.fokus?.id;
        if ((pass === 1) !== aktiv) continue;
        if (r.bb[2] < vx0 || r.bb[0] > vx1 || r.bb[3] < vy0 || r.bb[1] > vy1) continue;
        g.beginPath();
        const xy = r.xy;
        let letzter = -1e9, letzterY = -1e9;
        for (let i = 0; i < xy.length; i += 2) {
          const px = (xy[i] - cx) * s + b / 2, py = (xy[i + 1] - cy) * s + h / 2;
          if (i > 0 && i < xy.length - 2 && Math.abs(px - letzter) + Math.abs(py - letzterY) < 0.8) continue;
          if (i === 0) g.moveTo(px, py); else g.lineTo(px, py);
          letzter = px; letzterY = py;
        }
        g.globalCompositeOperation = aktiv || !p.dunkel ? "source-over" : "lighter";
        g.globalAlpha = aktiv ? 1 : p.dunkel ? 0.3 : 0.38;
        g.strokeStyle = aktiv ? css.getPropertyValue("--accent").trim() : farben[r.k];
        g.lineWidth = aktiv ? 3.4 : 1.7;
        g.stroke();
      }
    }
    g.globalAlpha = 1; g.globalCompositeOperation = "source-over";
  };
  const schedule = () => { if (!raf.current) raf.current = requestAnimationFrame(() => { raf.current = 0; zeichnen(); }); };

  // Groesse
  useEffect(() => {
    const el = wrap.current, c = cv.current;
    if (!el || !c) return;
    const messen = () => {
      const dpr = window.devicePixelRatio || 1, b = el.clientWidth, h = el.clientHeight;
      c.width = Math.round(b * dpr); c.height = Math.round(h * dpr);
      c.style.width = `${b}px`; c.style.height = `${h}px`;
      groesse.current = { b, h, dpr };
      schedule();
    };
    messen();
    const ro = new ResizeObserver(messen);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  // Einpassen bei neuen Daten oder "Alles zeigen"
  useEffect(() => { ansicht.current = einpassen(strecken, groesse.current.b, groesse.current.h, reset > 0); schedule(); }, [strecken, reset]);
  useEffect(() => { schedule(); }, [kacheln, dunkel]);
  // Suchtreffer: auf die Route zoomen
  useEffect(() => {
    if (!fokus) { schedule(); return; }
    const { b, h } = groesse.current, bw = Math.max(fokus.bb[2] - fokus.bb[0], 1e-6) * 1.7, bh = Math.max(fokus.bb[3] - fokus.bb[1], 1e-6) * 1.7;
    ansicht.current = { cx: (fokus.bb[0] + fokus.bb[2]) / 2, cy: (fokus.bb[1] + fokus.bb[3]) / 2, s: Math.min(TILE * 2 ** 17, b / bw, h / bh) };
    schedule();
  }, [fokus]);

  // Zoom und Verschieben
  useEffect(() => {
    const c = cv.current;
    if (!c) return;
    let zieh: { x: number; y: number; cx: number; cy: number; bewegt: boolean } | null = null;
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = c.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, { b, h } = groesse.current, a = ansicht.current;
      const f = Math.exp(-e.deltaY * 0.0016), ns = Math.max(TILE * 2 ** 3, Math.min(TILE * 2 ** 20, a.s * f));
      const wx = a.cx + (mx - b / 2) / a.s, wy = a.cy + (my - h / 2) / a.s;
      ansicht.current = { s: ns, cx: wx - (mx - b / 2) / ns, cy: wy - (my - h / 2) / ns };
      schedule();
    };
    const down = (e: MouseEvent) => { zieh = { x: e.clientX, y: e.clientY, cx: ansicht.current.cx, cy: ansicht.current.cy, bewegt: false }; };
    const move = (e: MouseEvent) => {
      if (zieh) {
        const dx = e.clientX - zieh.x, dy = e.clientY - zieh.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) zieh.bewegt = true;
        if (zieh.bewegt) { ansicht.current = { ...ansicht.current, cx: zieh.cx - dx / ansicht.current.s, cy: zieh.cy - dy / ansicht.current.s }; setTip(null); schedule(); return; }
      }
      const r = c.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, { b, h } = groesse.current, a = ansicht.current;
      let best: Strecke | null = null, bd = 7 * 7;
      for (const st of props.current.strecken) {
        const m = 8 / a.s;
        if (st.bb[2] + m < a.cx - b / 2 / a.s || st.bb[0] - m > a.cx + b / 2 / a.s || st.bb[3] + m < a.cy - h / 2 / a.s || st.bb[1] - m > a.cy + h / 2 / a.s) continue;
        const xy = st.xy;
        for (let i = 0; i + 3 < xy.length; i += 2) {
          const ax = (xy[i] - a.cx) * a.s + b / 2, ay = (xy[i + 1] - a.cy) * a.s + h / 2, bx = (xy[i + 2] - a.cx) * a.s + b / 2, by = (xy[i + 3] - a.cy) * a.s + h / 2;
          const vx = bx - ax, vy = by - ay, l2 = vx * vx + vy * vy;
          const t = l2 > 0 ? Math.max(0, Math.min(1, ((mx - ax) * vx + (my - ay) * vy) / l2)) : 0;
          const d = (ax + t * vx - mx) ** 2 + (ay + t * vy - my) ** 2;
          if (d < bd) { bd = d; best = st; }
        }
      }
      const neu = best ? best.id : null;
      if (neu !== treffer.current) { treffer.current = neu; schedule(); }
      setTip(best ? { x: mx, y: my, r: best } : null);
      c.style.cursor = best ? "pointer" : "grab";
    };
    const up = () => { const z = zieh; zieh = null; if (z && !z.bewegt && treffer.current) auf(treffer.current); };
    const leave = () => { zieh = null; if (treffer.current) { treffer.current = null; schedule(); } setTip(null); };
    c.addEventListener("wheel", wheel, { passive: false });
    c.addEventListener("mousedown", down);
    window.addEventListener("mouseup", up);
    c.addEventListener("mousemove", move);
    c.addEventListener("mouseleave", leave);
    return () => { c.removeEventListener("wheel", wheel); c.removeEventListener("mousedown", down); window.removeEventListener("mouseup", up); c.removeEventListener("mousemove", move); c.removeEventListener("mouseleave", leave); };
  }, [auf]);

  return (
    <div className="kartenflaeche" ref={wrap}>
      <canvas ref={cv} role="img" aria-label="Karte aller Routen" />
      {tip && <div className="tip" style={{ left: tip.x, top: tip.y, transform: `translate(${tip.x > groesse.current.b * 0.7 ? "calc(-100% - 14px)" : "14px"}, 12px)` }}><b>{tip.r.n}</b><div className="mono">{fmtTag(tip.r.tag, true)}</div></div>}
      {kacheln && <div className="attrib">© OpenStreetMap-Mitwirkende</div>}
    </div>
  );
}
