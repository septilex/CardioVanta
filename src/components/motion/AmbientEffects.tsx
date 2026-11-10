"use client";

import { useEffect } from "react";

/** Cards that tilt toward the cursor (with a soft sheen). */
const TILT = ".doc-card, .ax-journey-card, .ax-res-card, .doc-flow > li, .doc-next a";
/** Dark hero bands with a cursor-following spotlight. */
const SPOT = ".doc-hero, .lp-hero";
/** Primary buttons that lean toward the cursor. */
const MAGNET = ".ax-btn-continue, .ax-btn-submit, .doc-cta, .btn-primary, .lp-header-cta";

const MAX_TILT = 5; // degrees
const MAGNET_PULL = 0.18; // share of the cursor offset

/**
 * One delegated pointer listener for the whole site. It only writes CSS custom properties, at most
 * once per animation frame; all the visual work is CSS (transforms and gradients). Nothing runs on
 * touch-only devices or for people who prefer reduced motion.
 */
export function AmbientEffects() {
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!finePointer.matches || reduce.matches) return;

    let frame = 0;
    let last: PointerEvent | null = null;
    let tilted: HTMLElement | null = null;
    let magnet: HTMLElement | null = null;

    const release = (el: HTMLElement | null, props: string[]) => {
      if (!el) return;
      for (const p of props) el.style.removeProperty(p);
      el.removeAttribute("data-fx-active");
    };

    const apply = () => {
      frame = 0;
      const e = last;
      if (!e) return;
      const target = e.target instanceof Element ? e.target : null;

      const card = target?.closest<HTMLElement>(TILT) ?? null;
      if (card !== tilted) {
        release(tilted, ["--rx", "--ry", "--mx", "--my"]);
        tilted = card;
      }
      if (card) {
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width;
        const py = (e.clientY - r.top) / r.height;
        card.style.setProperty("--ry", `${((px - 0.5) * 2 * MAX_TILT).toFixed(2)}deg`);
        card.style.setProperty("--rx", `${((0.5 - py) * 2 * MAX_TILT).toFixed(2)}deg`);
        card.style.setProperty("--mx", `${(px * 100).toFixed(1)}%`);
        card.style.setProperty("--my", `${(py * 100).toFixed(1)}%`);
        card.setAttribute("data-fx-active", "");
      }

      const hero = target?.closest<HTMLElement>(SPOT);
      if (hero) {
        const r = hero.getBoundingClientRect();
        hero.style.setProperty("--sx", `${(e.clientX - r.left).toFixed(0)}px`);
        hero.style.setProperty("--sy", `${(e.clientY - r.top).toFixed(0)}px`);
        hero.setAttribute("data-fx-active", "");
      }

      const btn = target?.closest<HTMLElement>(MAGNET) ?? null;
      if (btn !== magnet) {
        release(magnet, ["--tx", "--ty"]);
        magnet = btn;
      }
      if (btn) {
        const r = btn.getBoundingClientRect();
        btn.style.setProperty("--tx", `${((e.clientX - (r.left + r.width / 2)) * MAGNET_PULL).toFixed(1)}px`);
        btn.style.setProperty("--ty", `${((e.clientY - (r.top + r.height / 2)) * MAGNET_PULL).toFixed(1)}px`);
        btn.setAttribute("data-fx-active", "");
      }
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      last = e;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    const onLeave = (e: PointerEvent) => {
      const target = e.target instanceof Element ? e.target : null;
      if (target?.matches(SPOT)) (target as HTMLElement).removeAttribute("data-fx-active");
    };
    const onOut = () => {
      release(tilted, ["--rx", "--ry", "--mx", "--my"]);
      release(magnet, ["--tx", "--ty"]);
      tilted = magnet = null;
    };

    document.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave, { capture: true, passive: true });
    document.documentElement.addEventListener("mouseleave", onOut);
    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave, { capture: true });
      document.documentElement.removeEventListener("mouseleave", onOut);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return null;
}
