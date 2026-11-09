"use client";

import * as React from "react";
import { NAV_BACK, NAV_FORWARD, NAV_LATERAL } from "../../lib/motion";

/*
 * React's <ViewTransition> ships in the React build that Next.js uses for the App Router (19.3 canary).
 * The standalone react@19.2 package that Jest renders with does not include it, so outside Next the
 * wrapper simply renders its children. Browsers without the View Transitions API also just swap pages.
 */
const ViewTransition = (React as Partial<typeof React>).ViewTransition;

/*
 * The browser skips a view transition when the tab is hidden or the viewport changes mid-way
 * (for example a phone's address bar collapsing) and rejects the transition's promises with an
 * InvalidStateError. Navigation still completes; only the animation is dropped. React leaves that
 * rejection unhandled, so it would surface as an uncaught console error. Handle exactly that case.
 */
if (typeof window !== "undefined") {
  const w = window as Window & { __cvViewTransitionGuard?: boolean };
  if (!w.__cvViewTransitionGuard) {
    w.__cvViewTransitionGuard = true;
    window.addEventListener("unhandledrejection", (event) => {
      const reason = event.reason as { name?: string; message?: string } | undefined;
      if (reason?.name === "InvalidStateError" && /^Transition was (aborted|skipped)/.test(reason.message ?? "")) {
        event.preventDefault();
      }
    });
  }
}

const ROUTE_CLASSES = {
  [NAV_FORWARD]: "cv-route-forward",
  [NAV_BACK]: "cv-route-back",
  [NAV_LATERAL]: "cv-route-lateral",
  default: "none",
};

/**
 * Wrap each page's root element. Navigations started by a <Link transitionTypes={[NAV_FORWARD]}> or
 * <Link transitionTypes={[NAV_BACK]}> crossfade the outgoing and incoming page (styles in globals.css).
 * Untyped navigations, such as the browser back button, swap instantly.
 */
export function RouteTransition({ children }: { children: React.ReactNode }) {
  if (!ViewTransition) return <>{children}</>;
  return (
    <ViewTransition enter={ROUTE_CLASSES} exit={ROUTE_CLASSES} default="none">
      {children}
    </ViewTransition>
  );
}
