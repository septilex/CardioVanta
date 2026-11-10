"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { CardioVantaTransitionLoader, HEART_SRC, type LoaderPhase } from "./CardioVantaTransitionLoader";

/** Routes that open with the brand loader. Overview and Heart Analysis never show it. */
export const LOADER_ROUTES: Record<string, string> = {
  "/research": "Research",
  "/about": "About",
};

export function loaderDestination(pathname: string | null | undefined): string | null {
  if (!pathname) return null;
  const clean = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return LOADER_ROUTES[clean] ?? null;
}

/** Sequence timings, in ms. The bar's own fill timing lives in CardioVantaTransitionLoader. */
export const LOADER_TIMING = {
  /** Let the ivory screen cover the old page before the route changes underneath. */
  pushDelay: 240,
  /** Shortest time the loader is on screen before it may complete (the bar's fill run). */
  minVisible: 1330,
  minVisibleReduced: 450,
  /** Final fill to 100%. */
  complete: 320,
  completeReduced: 140,
  /** Fade-out of the loader while the page rises in. */
  exit: 560,
  exitReduced: 200,
  /** The page's arrival animation; the marker on <html> is removed after it. */
  reveal: 760,
  /** Whatever happens (slow network, failed route), the loader leaves after this. */
  failsafe: 8000,
} as const;

type Phase = LoaderPhase | "idle";

const prefersReducedMotion = () =>
  typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

/**
 * Plays the CardioVanta loader whenever the user moves to Research or About, however they get there:
 * a link anywhere in the app (sidebar, mobile bar, landing header and footer, in-page links), the
 * browser's back and forward buttons, or opening the URL directly.
 *
 * Link clicks are intercepted so the loader is on screen *before* the route changes; the route is then
 * pushed underneath, and the loader leaves only once that route is actually showing (never a blank
 * page), or after a failsafe. Other routes are untouched.
 */
export function TransitionLoaderGate() {
  const pathname = usePathname();
  const router = useRouter();

  // Server render on a direct visit to /research or /about already includes the loader, so the page
  // never flashes before hydration.
  const [phase, setPhase] = useState<Phase>(() => (loaderDestination(pathname) ? "enter" : "idle"));
  const [destination, setDestination] = useState(() => loaderDestination(pathname) ?? "");
  const [runId, setRunId] = useState(0);
  const [initial, setInitial] = useState(() => Boolean(loaderDestination(pathname)));
  const [reduced, setReduced] = useState(false);

  const s = useRef({
    active: Boolean(loaderDestination(pathname)),
    phase: (loaderDestination(pathname) ? "enter" : "idle") as Phase,
    target: loaderDestination(pathname) ? pathname : (null as string | null),
    arrived: Boolean(loaderDestination(pathname)),
    minDone: false,
    reduced: false,
    timers: new Set<ReturnType<typeof setTimeout>>(),
    prevPath: null as string | null,
    /** Destinations replaced mid-run by a newer click; if one still lands first, it is not treated as arrival. */
    superseded: new Set<string>(),
  });

  const later = useCallback((fn: () => void, ms: number) => {
    const t = setTimeout(() => {
      s.current.timers.delete(t);
      fn();
    }, ms);
    s.current.timers.add(t);
  }, []);

  const clearTimers = useCallback(() => {
    s.current.timers.forEach(clearTimeout);
    s.current.timers.clear();
  }, []);

  const go = useCallback((next: Phase) => {
    s.current.phase = next;
    setPhase(next);
  }, []);

  const finish = useCallback(() => {
    const st = s.current;
    if (!st.active || st.phase === "exit" || st.phase === "idle") return;
    clearTimers();
    const html = document.documentElement;
    html.setAttribute("data-cv-reveal", "");
    go("exit");
    later(() => {
      st.active = false;
      st.target = null;
      go("idle");
      setInitial(false);
    }, st.reduced ? LOADER_TIMING.exitReduced : LOADER_TIMING.exit);
    later(() => html.removeAttribute("data-cv-reveal"), LOADER_TIMING.reveal);
  }, [clearTimers, go, later]);

  const tryComplete = useCallback(() => {
    const st = s.current;
    if (!st.active || st.phase !== "enter" || !st.arrived || !st.minDone) return;
    go("complete");
    later(finish, st.reduced ? LOADER_TIMING.completeReduced : LOADER_TIMING.complete);
  }, [finish, go, later]);

  /** Start (or restart) a run. `href` is pushed after the cover delay; omit it when the route is already showing. */
  const begin = useCallback(
    (path: string, href?: string) => {
      const st = s.current;
      const midRun = st.active && st.phase !== "exit";
      if (midRun && href && st.target && st.target !== path) st.superseded.add(st.target);
      else if (!midRun) st.superseded.clear();
      st.superseded.delete(path);
      clearTimers();
      document.documentElement.removeAttribute("data-cv-reveal");
      st.reduced = prefersReducedMotion();
      st.active = true;
      st.target = path;
      st.arrived = !href;
      st.minDone = false;
      setReduced(st.reduced);
      setDestination(loaderDestination(path) ?? "");
      setRunId((n) => n + 1);
      go("enter");
      if (href) {
        router.prefetch(href);
        later(() => router.push(href), LOADER_TIMING.pushDelay);
      }
      later(() => {
        st.minDone = true;
        tryComplete();
      }, st.reduced ? LOADER_TIMING.minVisibleReduced : LOADER_TIMING.minVisible);
      later(finish, LOADER_TIMING.failsafe);
    },
    [clearTimers, finish, go, later, router, tryComplete]
  );

  // Fetch and decode the heart artwork while the browser is idle, so the loader's first frame is cheap.
  useEffect(() => {
    const w = window as Window & { requestIdleCallback?: (cb: () => void) => number; cancelIdleCallback?: (id: number) => void };
    const warm = () => {
      const img = new Image();
      img.src = HEART_SRC;
      img.decode?.().catch(() => {});
    };
    if (w.requestIdleCallback) {
      const id = w.requestIdleCallback(warm);
      return () => w.cancelIdleCallback?.(id);
    }
    const t = setTimeout(warm, 1500);
    return () => clearTimeout(t);
  }, []);

  // Intercept link activation (mouse or keyboard Enter) to Research/About before Next's <Link> sees it.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const anchor = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor || (anchor.target && anchor.target !== "_self") || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      const path = url.pathname.length > 1 ? url.pathname.replace(/\/+$/, "") : url.pathname;
      if (!loaderDestination(path)) return;
      const st = s.current;
      const current = window.location.pathname.replace(/\/+$/, "") || "/";
      if (path === current) {
        // Already on this page (e.g. a #hash link): normal behaviour, unless the loader is still up.
        if (st.active && st.phase !== "exit") {
          e.preventDefault();
          e.stopImmediatePropagation();
        }
        return;
      }
      e.preventDefault();
      e.stopImmediatePropagation();
      if (st.active && st.phase !== "exit" && st.target === path) return; // duplicate click while on the way
      begin(path, url.pathname + url.search + url.hash);
    };
    window.addEventListener("click", onClick, true);
    return () => window.removeEventListener("click", onClick, true);
  }, [begin]);

  // Route changes: arrival of a pushed route, or back/forward and other navigation we did not start.
  useLayoutEffect(() => {
    const st = s.current;
    const path = pathname ?? "";
    const prev = st.prevPath;
    st.prevPath = path;

    if (prev === null) {
      // First render. On a direct visit the server already rendered the loader; start its clock.
      if (st.active) {
        st.reduced = prefersReducedMotion();
        setReduced(st.reduced);
        later(() => {
          st.minDone = true;
          tryComplete();
        }, st.reduced ? LOADER_TIMING.minVisibleReduced : LOADER_TIMING.minVisible);
        later(finish, LOADER_TIMING.failsafe);
      }
      return;
    }
    if (prev === path) return;

    if (st.active && st.phase !== "exit") {
      if (path === st.target) {
        st.arrived = true;
        tryComplete();
      } else if (st.superseded.has(path)) {
        // An earlier click's route landed before the newer one: keep waiting for the newer one.
      } else if (loaderDestination(path)) {
        // e.g. Back pressed mid-run onto the other loader page: that page is already here.
        st.target = path;
        st.arrived = true;
        setDestination(loaderDestination(path) ?? "");
        tryComplete();
      } else {
        finish(); // left for a page without the loader: get out of the way
      }
      return;
    }
    if (loaderDestination(path)) begin(path); // back/forward or a programmatic push into Research/About
  }, [pathname, begin, finish, later, tryComplete]);

  useEffect(
    () => () => {
      clearTimers();
      document.documentElement.removeAttribute("data-cv-reveal");
      // React's development double-mount runs this and then mounts again: re-arm from scratch.
      s.current.prevPath = null;
    },
    [clearTimers]
  );

  if (phase === "idle") return null;
  return (
    <CardioVantaTransitionLoader
      key={runId}
      phase={phase}
      destination={destination}
      initial={initial && runId === 0}
      reducedMotion={reduced}
    />
  );
}
