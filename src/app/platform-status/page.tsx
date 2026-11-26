import type { Metadata } from "next";
import { getPlatformHealth } from "../../lib/platformStatus";
import "./platform-status.css";

export const metadata: Metadata = {
  title: "Platform status | CardioVanta",
  description: "Current availability of the CardioVanta backend and model-serving service.",
};

// This route reads live health at request time; it must not be generated at build time.
export const dynamic = "force-dynamic";

export default async function PlatformStatusPage() {
  const [health] = await Promise.all([getPlatformHealth()]);
  const checkedAt = new Date().toISOString();

  return (
    <main className="platform-status-page">
      <div className="platform-status-wrap">
        <a className="platform-status-brand" href="/" aria-label="CardioVanta home">
          <span aria-hidden="true" className="platform-status-mark">C</span>
          <span>CardioVanta</span>
        </a>

        <section className="platform-status-content" aria-labelledby="platform-status-title">
          <p className="platform-status-kicker">Service availability</p>
          <h1 id="platform-status-title">Platform status</h1>
          <p className="platform-status-intro">A live check of the services that support CardioVanta.</p>

          <div className="platform-status-list" aria-label="Platform services">
            <div className="platform-status-row">
              <div>
                <h2>Backend API</h2>
                <p>Responds to a health check request</p>
              </div>
              <StatusValue available={health.backendAvailable} />
            </div>
            <div className="platform-status-row">
              <div>
                <h2>Model service</h2>
                <p>Model package loaded and ready to serve</p>
              </div>
              <StatusValue available={health.modelServiceAvailable} />
            </div>
          </div>

          <p className="platform-status-checked">
            Last checked <time dateTime={checkedAt}>{new Date(checkedAt).toLocaleString("en", { timeZone: "UTC", timeZoneName: "short" })}</time>
          </p>
          <p className="platform-status-note">This check reports service availability only. It does not create or assess a prediction.</p>
        </section>
      </div>
    </main>
  );
}

function StatusValue({ available }: { available: boolean }) {
  return (
    <span className={`platform-status-value ${available ? "is-available" : "is-unavailable"}`}>
      <span className="platform-status-dot" aria-hidden="true" />
      {available ? "Available" : "Unavailable"}
    </span>
  );
}
