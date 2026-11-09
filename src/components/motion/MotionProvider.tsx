"use client";

import { LazyMotion, MotionConfig, domAnimation } from "framer-motion";
import { TRANSITION } from "../../lib/motion";

/**
 * Motion policy for a page tree:
 * - LazyMotion + domAnimation loads only the animation features the assessment needs (no layout or
 *   drag), and `strict` makes any accidental full `motion.*` import fail loudly in development.
 * - reducedMotion="user" follows the operating-system setting: transforms are skipped, opacity
 *   fades remain, so content is never hidden or delayed.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user" transition={TRANSITION.enter}>
        {children}
      </MotionConfig>
    </LazyMotion>
  );
}
