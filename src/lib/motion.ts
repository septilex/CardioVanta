/**
 * CardioVanta motion system: the single source of truth for timing, easing and shared variants.
 *
 * - JavaScript (framer-motion) reads the tokens below.
 * - CSS reads the same values as custom properties in src/app/globals.css (--cv-ease-*, --cv-dur-*,
 *   --cv-stagger). __tests__/motion.test.ts fails if the two drift apart.
 *
 * Principles
 * - Motion explains a change of state; it never decorates idle content (no infinite loops except
 *   loading indicators that exist only while a request is actually in flight).
 * - Arrivals use EASE.out and DURATION.base/slow; departures are quicker (EASE.in, DURATION.fast) so
 *   leaving content never competes with arriving content.
 * - Only opacity and transforms are animated, except the error banner's height, which is a single
 *   small element.
 * - Numbers and bars animate to the exact values returned by the API; nothing is invented.
 * - prefers-reduced-motion: MotionConfig reducedMotion="user" (framer) and the CSS media queries in
 *   globals.css / assessment.css remove movement while keeping content immediately visible.
 */
import type { Transition, Variants } from "framer-motion";

/** Cubic-bézier curves. `out` is the house curve (also used by the landing page since launch). */
export const EASE = {
  out: [0.22, 1, 0.36, 1],
  inOut: [0.65, 0, 0.35, 1],
  in: [0.4, 0, 1, 1],
} as const;

/** Durations in seconds (framer-motion units). CSS mirrors them in milliseconds. */
export const DURATION = {
  /** Press and release feedback. */
  press: 0.12,
  /** Hovers, colour changes and exits. */
  fast: 0.18,
  /** Most state changes and arrivals. */
  base: 0.28,
  /** Panels and page-level arrivals. */
  slow: 0.45,
  /** Scroll reveals on the landing page. */
  reveal: 0.7,
  /** Count-ups, gauges and bar growth. */
  count: 0.9,
} as const;

/** Delay between siblings in a staggered group, in seconds. */
export const STAGGER = {
  tight: 0.04,
  base: 0.07,
  loose: 0.12,
} as const;

export const TRANSITION = {
  enter: { duration: DURATION.base, ease: EASE.out },
  enterSlow: { duration: DURATION.slow, ease: EASE.out },
  exit: { duration: DURATION.fast, ease: EASE.in },
  count: { duration: DURATION.count, ease: EASE.out },
} as const satisfies Record<string, Transition>;

/* ─── Assessment & analysis ─────────────────────────────────────────────────────────────── */

/** Form card ⇄ results panel. The panel arrives, then reveals its children in sequence. */
export const panelSwap: Variants = {
  initial: { opacity: 0, y: 14 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { ...TRANSITION.enterSlow, when: "beforeChildren", staggerChildren: STAGGER.base },
  },
  exit: { opacity: 0, y: -8, transition: TRANSITION.exit },
};

/** Parent of a staggered reveal. */
export const revealGroup: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: STAGGER.base, delayChildren: STAGGER.tight } },
};

/** Child of a staggered reveal. */
export const revealItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: TRANSITION.enter },
};

/** Banners that push content: height is animated so surrounding content glides instead of jumping. */
export const collapse: Variants = {
  initial: { opacity: 0, height: 0 },
  animate: { opacity: 1, height: "auto", transition: TRANSITION.enter },
  exit: { opacity: 0, height: 0, transition: TRANSITION.exit },
};

/*
 * Contribution bars grow with a CSS animation (assessment.css, `ax-bar-fill`) using the same
 * --cv-dur-count / --cv-stagger-tight tokens: hidden tab panels are display:none, so CSS replays the
 * growth whenever a panel is shown, with no per-bar JavaScript.
 *
 * Inside scroll containers (the card body, the summary rail, the results body), entrances fade
 * without moving: movement there forces a scrollable-area recalculation on every frame.
 */

/* ─── Landing page presets (moved here unchanged from src/app/page.tsx) ─────────────────── */

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.reveal, ease: EASE.out } },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.8 } },
};

export const stagger: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: STAGGER.loose } },
};

export const staggerFast: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

export const slideLeft: Variants = {
  hidden: { opacity: 0, x: -40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: EASE.out } },
};

export const slideRight: Variants = {
  hidden: { opacity: 0, x: 40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: EASE.out } },
};

export const clipReveal: Variants = {
  hidden: { clipPath: "inset(0 100% 0 0)" },
  visible: { clipPath: "inset(0 0% 0 0)", transition: { duration: 1.2, ease: EASE.out } },
};

/* ─── Route transitions (React <ViewTransition> + <Link transitionTypes>) ───────────────── */

/** Moving deeper into the product (landing → assessment). */
export const NAV_FORWARD = "nav-forward";
/** Returning towards the landing page. */
export const NAV_BACK = "nav-back";

/* ─── Helpers ───────────────────────────────────────────────────────────────────────────── */

/** Formats a probability exactly the way the results panel prints it (one decimal, percent). */
export function formatProbability(probability: number): string {
  return (probability * 100).toFixed(1);
}
