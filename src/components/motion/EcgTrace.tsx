/**
 * A heartbeat trace that draws itself once when the page opens (CSS only, no loop).
 * Decorative; hidden from assistive technology. Styles: .cv-ecg in globals.css.
 */
export function EcgTrace({ className }: { className?: string }) {
  return (
    <svg
      className={className ? `cv-ecg ${className}` : "cv-ecg"}
      viewBox="0 0 320 60"
      fill="none"
      aria-hidden="true"
      focusable="false"
      preserveAspectRatio="none"
    >
      <path
        pathLength={1}
        d="M0 34 H92 l8 -6 l8 6 H132 l6 10 l10 -42 l10 50 l8 -18 H210 l10 -8 l12 8 H320"
      />
    </svg>
  );
}
