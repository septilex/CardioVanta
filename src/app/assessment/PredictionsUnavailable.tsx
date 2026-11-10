import Link from "next/link";
import type { CSSProperties } from "react";
import { NAV_BACK, NAV_LATERAL } from "../../lib/motion";

const BACK = [NAV_BACK];
const LATERAL = [NAV_LATERAL];
const order = (i: number) => ({ "--cv-i": i }) as CSSProperties;

/**
 * Shown instead of the assessment form while predictions are unavailable
 * (configs/prediction_service.json). It renders no form and sends no request.
 * Motion is CSS-only (a staggered entrance) and adds no controls, status regions or numbers.
 */
export default function PredictionsUnavailable({ notice }: { notice: string }) {
  return (
    <main className="ax-unavailable" aria-labelledby="ax-unavailable-title">
      <section className="ax-unavailable-card cv-rise" style={order(0)}>
        <Link href="/" transitionTypes={BACK} className="ax-unavailable-logo-link cv-rise" style={order(1)} title="CardioVanta Home">
          <img
            src="/brand/cardiovanta-horizontal-transparent.png"
            alt="CardioVanta | Intelligent Cardiovascular Insight"
            className="ax-unavailable-logo"
          />
        </Link>
        <p className="ax-unavailable-eyebrow cv-rise" style={order(2)}>
          <span className="ax-unavailable-dot" aria-hidden="true" />
          Heart analysis paused
        </p>
        <h1 id="ax-unavailable-title" className="ax-unavailable-title cv-rise" style={order(3)}>
          Predictions are temporarily unavailable
        </h1>
        <p className="ax-unavailable-notice cv-rise" style={order(4)} role="status">
          {notice}
        </p>
        <p className="ax-unavailable-detail cv-rise" style={order(5)}>
          The assessment form is switched off until the prediction service has been verified. Nothing is entered or
          sent from this page.
        </p>
        <Link href="/" transitionTypes={BACK} className="ax-unavailable-link cv-rise" style={order(6)}>
<span className="ax-btn-arrow ax-btn-arrow--back" aria-hidden="true">←</span> Return to the home page
        </Link>
        <p className="ax-unavailable-more cv-rise" style={order(7)}>
          While you wait: <Link href="/research" transitionTypes={LATERAL}>read the research</Link> or{" "}
          <Link href="/about" transitionTypes={LATERAL}>learn how CardioVanta works</Link>.
        </p>
      </section>
    </main>
  );
}
