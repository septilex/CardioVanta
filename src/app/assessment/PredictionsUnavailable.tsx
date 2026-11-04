import Link from "next/link";

/**
 * Shown instead of the assessment form while predictions are unavailable
 * (configs/prediction_service.json). It renders no form and sends no request.
 */
export default function PredictionsUnavailable({ notice }: { notice: string }) {
  return (
    <main className="ax-unavailable" aria-labelledby="ax-unavailable-title">
      <section className="ax-unavailable-card">
        <a href="/" className="ax-unavailable-logo-link" title="CardioVanta Home">
          <img
            src="/brand/cardiovanta-horizontal-transparent.png"
            alt="CardioVanta | Intelligent Cardiovascular Insight"
            className="ax-unavailable-logo"
          />
        </a>
        <p className="ax-unavailable-eyebrow">Heart analysis paused</p>
        <h1 id="ax-unavailable-title" className="ax-unavailable-title">
          Predictions are temporarily unavailable
        </h1>
        <p className="ax-unavailable-notice" role="status">
          {notice}
        </p>
        <p className="ax-unavailable-detail">
          The assessment form is switched off until the prediction service has been verified. Nothing is entered or
          sent from this page.
        </p>
        <Link href="/" className="ax-unavailable-link">
          Return to the home page
        </Link>
      </section>
    </main>
  );
}
