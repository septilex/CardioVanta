"use client";

import { useEffect } from "react";

/** How much of the remaining distance is covered each frame. Lower = longer, silkier glide. */
const EASE = 0.085;

/** True if `el` (or an ancestor below <body>) can itself scroll in the wheel's direction. */
function innerScroller(el: Element | null, dy: number): boolean {
  for (let n = el; n && n !== document.body && n !== document.documentElement; n = n.parentElement) {
    const s = getComputedStyle(n);
    if (!/(auto|scroll|overlay)/.test(s.overflowY) || n.scrollHeight <= n.clientHeight) continue;
    if (dy > 0 ? n.scrollTop + n.clientHeight < n.scrollHeight - 1 : n.scrollTop > 0) return true;
  }
  return false;
}

/**
 * Premium inertial page scrolling: mouse-wheel input glides to its target with a soft ease-out
 * instead of jumping. Touch, keyboard, scrollbar and inner scroll areas stay native; reduced
 * motion and pinch-zoom are left alone.
 */
export function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let target = window.scrollY;
    let current = window.scrollY;
    let raf = 0;
    let lastSet = -1;

    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };

    const tick = () => {
      current += (target - current) * EASE;
      if (Math.abs(target - current) < 0.5) current = target;
      lastSet = Math.round(current);
      window.scrollTo({ top: current, behavior: "instant" as ScrollBehavior });
      raf = current === target ? 0 : requestAnimationFrame(tick);
    };

    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.defaultPrevented || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      if (document.querySelector(".ldr-root")) return; // brand loader on screen
      if (innerScroller(e.target as Element, e.deltaY)) return;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      if (max <= 0) return;
      e.preventDefault();
      if (!raf) current = target = window.scrollY;
      const unit = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? window.innerHeight : 1;
      target = Math.max(0, Math.min(max, target + e.deltaY * unit));
      if (!raf) raf = requestAnimationFrame(tick);
    };

    // Any scroll we did not make (keys, scrollbar, anchors, route change) takes over.
    const onScroll = () => {
      if (raf && Math.abs(window.scrollY - lastSet) <= 2) return;
      stop();
      current = target = window.scrollY;
    };

    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      stop();
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return null;
}
