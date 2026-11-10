"use client";

import { useEffect, useRef } from "react";
import "./transition-loader.css";

/** The anatomical heart, extracted from the brand reference with its glow kept as transparency. */
export const HEART_SRC = "/images/loader-heart.webp";

/** Where the loader is in its sequence. `complete` fills the bar to 100%; `exit` fades the screen out. */
export type LoaderPhase = "enter" | "complete" | "exit";

interface LoaderProps {
  phase: LoaderPhase;
  /** Destination name, read to assistive technology ("Loading Research"). */
  destination: string;
  /** Rendered by the server on a direct page load: start fully opaque so the page never flashes. */
  initial?: boolean;
  reducedMotion: boolean;
}

/* ─── Static SVG geometry (computed once) ────────────────────────────────────────────────────── */

/** Tick marks around the heart; the bottom arc is left open for the wordmark, as in the reference. */
const TICKS = Array.from({ length: 90 }, (_, i) => i * 4)
  .filter((deg) => deg < 132 || deg > 228)
  .map((deg) => {
    const major = deg % 20 === 0;
    const rad = ((deg - 90) * Math.PI) / 180;
    const r1 = 300;
    const r2 = r1 + (major ? 15 : 8);
    const f = (n: number) => Math.round(n * 10) / 10;
    return { x1: f(Math.cos(rad) * r1), y1: f(Math.sin(rad) * r1), x2: f(Math.cos(rad) * r2), y2: f(Math.sin(rad) * r2), major };
  });

/** Concentric rings of fine dots that fade outward (each ring is one dashed circle). */
const DOT_RINGS = [
  { r: 196, gap: 6.5, o: 0.5 },
  { r: 212, gap: 8, o: 0.34 },
  { r: 228, gap: 9.5, o: 0.26 },
  { r: 246, gap: 11.5, o: 0.18 },
  { r: 266, gap: 14, o: 0.12 },
];

/**
 * Corner ribbon: a silk band of strands sweeping from the top edge to the left edge. The strands'
 * order flips along the way (the right-most start ends highest), so the band twists on itself like
 * the folded ribbon in the reference.
 */
const STRAND_COUNT = 13;
const strand = (k: number) => {
  const sx = 170 + k * 21; // where it leaves the top edge
  const ey = 520 - k * 10; // where it meets the left edge
  return {
    start: [sx, -12],
    c1: [sx - 30 - k * 4, 120 + k * 7],
    c2: [235 - k * 9, 225 + k * 3],
    end: [-12, ey],
  };
};
const RIBBON_STRANDS = Array.from({ length: STRAND_COUNT }, (_, k) => {
  const p = strand(k);
  return {
    d: `M ${p.start} C ${p.c1} ${p.c2} ${p.end}`,
    w: k % 4 === 0 ? 1.7 : k % 2 === 0 ? 1.1 : 0.75,
    o: 0.45 + 0.4 * Math.sin((k / (STRAND_COUNT - 1)) * Math.PI),
    k,
  };
});
/** Translucent sheets between the outer strands (each traced out along one strand and back along the other). */
const sheet = (a: number, b: number) => {
  const p = strand(a);
  const q = strand(b);
  return `M ${p.start} C ${p.c1} ${p.c2} ${p.end} L ${q.end} C ${q.c2} ${q.c1} ${q.start} Z`;
};
const RIBBON_BAND_A = sheet(0, STRAND_COUNT - 1);
const RIBBON_BAND_B = sheet(3, 9);

function Ribbon({ corner }: { corner: "tl" | "br" }) {
  const id = `ldr-rib-${corner}`;
  return (
    <svg className={`ldr-ribbon ldr-ribbon-${corner}`} viewBox="0 0 640 560" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-s`} x1="1" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#E3242B" stopOpacity="0" />
          <stop offset="0.35" stopColor="#E3242B" stopOpacity="0.9" />
          <stop offset="0.75" stopColor="#F04848" stopOpacity="0.65" />
          <stop offset="1" stopColor="#F04848" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={`${id}-f`} x1="1" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F23B3B" stopOpacity="0" />
          <stop offset="0.45" stopColor="#F23B3B" stopOpacity="0.2" />
          <stop offset="1" stopColor="#F23B3B" stopOpacity="0" />
        </linearGradient>
      </defs>
      <g className="ldr-ribbon-drift">
        <path className="ldr-band" d={RIBBON_BAND_A} fill={`url(#${id}-f)`} />
        <path className="ldr-band ldr-band-b" d={RIBBON_BAND_B} fill={`url(#${id}-f)`} />
        {RIBBON_STRANDS.map((s) => (
          <path
            key={s.k}
            className="ldr-strand"
            d={s.d}
            pathLength={1}
            stroke={`url(#${id}-s)`}
            strokeWidth={s.w}
            strokeOpacity={s.o}
            style={{ "--k": s.k } as React.CSSProperties}
          />
        ))}
      </g>
    </svg>
  );
}

/** Three stacked layers so each can turn independently on the compositor. */
function Halo() {
  const layer = { viewBox: "-330 -330 660 660", fill: "none", "aria-hidden": true, focusable: false } as const;
  return (
    <div className="ldr-halo">
      <svg className="ldr-layer ldr-ticks" {...layer}>
        {TICKS.map((t, i) => (
          <line
            key={i}
            x1={t.x1}
            y1={t.y1}
            x2={t.x2}
            y2={t.y2}
            stroke="#D41F2C"
            strokeOpacity={t.major ? 0.85 : 0.5}
            strokeWidth={t.major ? 2 : 1.4}
            strokeLinecap="round"
          />
        ))}
      </svg>
      <svg className="ldr-layer ldr-dots" {...layer}>
        {DOT_RINGS.map((ring) => (
          <circle
            key={ring.r}
            r={ring.r}
            stroke="#E3242B"
            strokeOpacity={ring.o}
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray={`0 ${ring.gap}`}
          />
        ))}
      </svg>
      <svg className="ldr-layer ldr-arcs" {...layer}>
        <circle r={180} stroke="#E3242B" strokeOpacity={0.28} strokeWidth={1} strokeDasharray="120 40 30 60 200 80" />
        <circle r={284} stroke="#E3242B" strokeOpacity={0.16} strokeWidth={1} strokeDasharray="60 120 220 90" />
      </svg>
    </div>
  );
}

/**
 * The CardioVanta brand screen shown while moving to Research or About: ivory backdrop with corner
 * ribbons, the glowing anatomical heart inside its technical halo, the wordmark, a progress bar and a
 * LOADING label. The bar tracks the page transition only; it has nothing to do with model computation.
 */
export function CardioVantaTransitionLoader({ phase, destination, initial = false, reducedMotion }: LoaderProps) {
  const fillRef = useRef<HTMLSpanElement>(null);
  const runRef = useRef<Animation | null>(null);

  // The bar fill is driven with the Web Animations API so `complete` can continue from wherever the
  // fill currently is (no jump back), and everything stays on the compositor (transform only).
  useEffect(() => {
    const el = fillRef.current;
    if (!el || typeof el.animate !== "function") return;
    const ease = "cubic-bezier(0.22, 1, 0.36, 1)";
    if (phase === "enter") {
      const run = el.animate(
        [{ transform: "translateX(-100%)" }, { transform: "translateX(-12%)" }],
        reducedMotion
          ? { duration: 350, easing: "linear", fill: "forwards" }
          : { duration: 950, delay: 380, easing: "cubic-bezier(0.45, 0, 0.2, 1)", fill: "forwards" }
      );
      runRef.current = run;
      // If the destination is slow to arrive, keep creeping instead of sitting still.
      run.onfinish = () => {
        if (runRef.current !== run) return;
        runRef.current = el.animate([{ transform: "translateX(-12%)" }, { transform: "translateX(-4%)" }], {
          duration: 5000,
          easing: ease,
          fill: "forwards",
        });
      };
    } else if (phase === "complete") {
      const from = getComputedStyle(el).transform;
      runRef.current?.cancel();
      runRef.current = el.animate([{ transform: from === "none" ? "translateX(-12%)" : from }, { transform: "translateX(0)" }], {
        duration: reducedMotion ? 120 : 300,
        easing: ease,
        fill: "forwards",
      });
    }
  }, [phase, reducedMotion]);

  useEffect(() => () => runRef.current?.cancel(), []);

  return (
    <div
      className="ldr-root"
      data-phase={phase}
      data-initial={initial ? "true" : undefined}
      data-reduced={reducedMotion ? "true" : undefined}
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Loading {destination}</span>
      <div className="ldr-atmos" aria-hidden="true" />
      <Ribbon corner="tl" />
      <Ribbon corner="br" />

      <div className="ldr-stage" aria-hidden="true">
        <div className="ldr-heart-box">
          <Halo />
          <div className="ldr-heart-glow" />
          <div className="ldr-heart-in">
            <div className="ldr-heart-beat">
              {/* eslint-disable-next-line @next/next/no-img-element -- decorative, preloaded, fixed size */}
              <img className="ldr-heart" src={HEART_SRC} alt="" width={380} height={430} decoding="async" fetchPriority="high" draggable={false} />
            </div>
          </div>
        </div>

        <p className="ldr-title">CARDIOVANTA</p>

        <div className="ldr-bar">
          <span className="ldr-track">
            <span ref={fillRef} className="ldr-fill" />
          </span>
        </div>

        <p className="ldr-label">LOADING</p>
      </div>
    </div>
  );
}
