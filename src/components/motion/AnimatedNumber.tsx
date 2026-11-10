"use client";

import { useEffect, useRef } from "react";
import { animate, useReducedMotion } from "framer-motion";
import { TRANSITION } from "../../lib/motion";

interface AnimatedNumberProps {
  /** The exact value to show once the animation has finished. */
  value: number;
  /** Formats every frame; the final frame uses `value` itself, so rounding never drifts. */
  format: (n: number) => string;
  /** Seconds to wait before counting. */
  delay?: number;
  className?: string;
}

/**
 * Counts from zero to `value`. It is purely visual: the element is aria-hidden, so the caller must
 * render the exact value as text for assistive technology. With reduced motion, or when the browser
 * cannot animate, the exact value is shown immediately.
 *
 * The text is written straight to the DOM node on each frame instead of through React state, so the
 * count-up costs one text update per frame and no re-renders.
 */
export function AnimatedNumber({ value, format, delay = 0, className }: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduce) {
      node.textContent = format(value);
      return;
    }
    // Start from zero straight away so a delayed count-up never flashes the final value first.
    node.textContent = format(0);
    const controls = animate(0, value, {
      ...TRANSITION.count,
      delay,
      onUpdate: (latest) => {
        node.textContent = format(latest);
      },
      onComplete: () => {
        node.textContent = format(value);
      },
    });
    return () => controls.stop();
  }, [value, format, delay, reduce]);

  // Server and first paint show the exact value, so nothing is wrong if JavaScript is slow.
  return (
    <span ref={ref} className={className} aria-hidden="true">
      {format(value)}
    </span>
  );
}
