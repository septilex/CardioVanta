"use client";

import { useEffect, useRef } from "react";
import { animate } from "framer-motion";
import { TRANSITION } from "../../lib/motion";

interface CountUpProps {
  /** The exact text to end on, e.g. "0.911" or "242". Shown as-is before and after the count. */
  value: string;
  className?: string;
}

/**
 * Counts up to a figure the first time it scrolls into view, then shows exactly `value`.
 * The exact text is server-rendered and kept for assistive technology (sr-only); the counting copy
 * is aria-hidden. Without IntersectionObserver, or with reduced motion, nothing animates.
 */
export function CountUp({ value, className }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const node = ref.current;
    const target = Number(value.replace(/,/g, ""));
    if (!node || !Number.isFinite(target) || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const decimals = (value.split(".")[1] ?? "").length;
    let stop: (() => void) | undefined;
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((en) => en.isIntersecting)) return;
        io.disconnect();
        node.textContent = (0).toFixed(decimals);
        const controls = animate(0, target, {
          ...TRANSITION.count,
          onUpdate: (v) => {
            node.textContent = v.toFixed(decimals);
          },
          onComplete: () => {
            node.textContent = value;
          },
        });
        stop = () => controls.stop();
      },
      { threshold: 0.6 }
    );
    io.observe(node);
    return () => {
      io.disconnect();
      stop?.();
      node.textContent = value;
    };
  }, [value]);

  return (
    <span className={className}>
      <span ref={ref} aria-hidden="true">
        {value}
      </span>
      <span className="sr-only">{value}</span>
    </span>
  );
}
