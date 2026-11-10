import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import { DocShell } from "../../components/shell/DocShell";
import { NAV_BACK, NAV_LATERAL } from "../../lib/motion";

export const metadata: Metadata = {
  title: "About | CardioVanta",
  description:
    "What CardioVanta is, why it exists and how it turns 13 clinical measurements into an explained, calibrated probability.",
};

const order = (i: number) => ({ "--cv-i": i }) as CSSProperties;

const icon = (path: ReactNode) => (
  <span className="doc-card-icon" aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {path}
    </svg>
  </span>
);

const FLOW: { title: string; body: ReactNode }[] = [
  {
    title: "Clinical inputs",
    body: (
      <>
        13 measurements entered in four steps. The API checks them against a model generated from the feature contract
        and rejects unknown, missing or non-finite values.
      </>
    ),
  },
  {
    title: "Feature processing",
    body: (
      <>
        Inputs are put in contract order. Five continuous values are standardised, three binary values pass through and
        five categorical values are one-hot encoded.
      </>
    ),
  },
  {
    title: "Machine-learning model",
    body: (
      <>
        Model <code>cardiovanta-lr13</code> 1.0.0: class-balanced logistic regression. The registry verifies every file&apos;s
        SHA-256 before loading it.
      </>
    ),
  },
  {
    title: "Probability estimation",
    body: (
      <>
        Five sigmoid-calibrated members are averaged into the probability of significant obstructive coronary artery
        disease, read from the disease label the model declares.
      </>
    ),
  },
  {
    title: "Explanation",
    body: (
      <>
        Linear and SHAP-equivalent contributions show what moved the estimate, with warnings for inputs outside the
        development range and no default decision threshold.
      </>
    ),
  },
];

const DIFFERENT: { title: string; body: string; icon: ReactNode }[] = [
  {
    title: "Probability transparency",
    body: "Every result states exactly what the number estimates, and that no validated decision threshold exists.",
    icon: <><path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-6" /></>,
  },
  {
    title: "Model calibration",
    body: "Probabilities are calibrated so that their size means something, and calibration is studied openly.",
    icon: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></>,
  },
  {
    title: "Explainability",
    body: "Each estimate comes with the inputs that pushed it up or down, labelled as model behaviour, not causes.",
    icon: <><path d="M9 18h6" /><path d="M10 22h4" /><path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z" /></>,
  },
  {
    title: "Model versioning",
    body: "A model is an immutable, explicitly versioned package. Changing it means releasing a new version.",
    icon: <><path d="M12 2l9 5-9 5-9-5 9-5z" /><path d="M3 12l9 5 9-5" /><path d="M3 17l9 5 9-5" /></>,
  },
  {
    title: "Research reproducibility",
    body: "Studies are designed and hashed before they run, and their code, results and tests live in the repository.",
    icon: <><path d="M4 4h16v16H4z" /><path d="M4 9h16" /><path d="M9 4v16" /></>,
  },
  {
    title: "Honest uncertainty",
    body: "Unverified inputs, development-range limits and open problems are shown rather than hidden.",
    icon: <><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></>,
  },
];

const TECH: { group: string; items: string[] }[] = [
  { group: "Web application", items: ["Next.js 16 (App Router)", "React 19", "TypeScript", "Framer Motion", "Plain CSS"] },
  { group: "Prediction API", items: ["FastAPI", "Pydantic 2", "Python 3.12", "Vercel Python function"] },
  { group: "Machine learning", items: ["scikit-learn 1.9", "pandas and NumPy", "cardiovanta_ml package", "SHA-256 model registry"] },
  { group: "Quality and process", items: ["GitHub Actions", "pytest and Jest", "OpenSpec pre-registration", "Research-data quarantine"] },
];

export default function AboutPage() {
  return (
    <DocShell section="About">
      <section className="doc-hero" aria-labelledby="about-title">
        <div className="doc-hero-inner">
          <p className="doc-hero-eyebrow cv-rise" style={order(0)}>About</p>
          <h1 id="about-title" className="cv-rise" style={order(1)}>About CardioVanta</h1>
          <p className="doc-hero-tagline cv-rise" style={order(2)}>
            Know the risk. Know the why. Know how far to trust it.
          </p>
          <p className="doc-hero-lede cv-rise" style={order(3)}>
            CardioVanta is a cardiovascular machine-learning research and assessment platform. From 13 structured
            measurements it estimates the probability of significant obstructive coronary artery disease, shows which
            inputs moved that estimate, and says how far the estimate can be trusted.
          </p>
        </div>
      </section>

      <div className="doc-body">
        <section className="doc-section" aria-labelledby="purpose">
          <div className="reveal">
            <p className="doc-eyebrow">Our purpose</p>
            <h2 id="purpose">Making cardiovascular machine learning understandable</h2>
            <div className="doc-prose">
              <p>
                Many heart-disease models publish a single accuracy figure and a yes-or-no answer. Behind it there is often
                an uncalibrated score, no explanation, and sometimes an outcome pointing the wrong way. CardioVanta sets out
                to do the opposite, in the open, so that each step from measurement to estimate can be inspected.
              </p>
            </div>
          </div>
          <div className="doc-grid">
            <article className="doc-card reveal">
              <h3>Know the risk</h3>
              <p>A calibrated probability that disease is present, with its orientation taken from the model&apos;s own metadata.</p>
            </article>
            <article className="doc-card reveal">
              <h3>Know the why</h3>
              <p>The inputs that pushed the estimate up or down, with plain statements of what those explanations can and cannot mean.</p>
            </article>
            <article className="doc-card reveal">
              <h3>Know how far to trust it</h3>
              <p>Warnings for inputs outside the development data, the verification status of every input code, and no default threshold.</p>
            </article>
          </div>
        </section>

        <section className="doc-section" aria-labelledby="how">
          <div className="reveal">
            <p className="doc-eyebrow">How CardioVanta works</p>
            <h2 id="how">From measurements to an explained estimate</h2>
          </div>
          <ol className="doc-flow">
            {FLOW.map((step) => (
              <li key={step.title} className="reveal">
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
          <div className="doc-callout is-info reveal">
            <p>
              The site and the prediction API are one stateless deployment: no accounts, no database and no stored health
              data. Each request is answered and forgotten.
            </p>
          </div>
        </section>

        <section className="doc-section" aria-labelledby="different">
          <div className="reveal">
            <p className="doc-eyebrow">What makes it different</p>
            <h2 id="different">Built to be checked, not just believed</h2>
          </div>
          <div className="doc-grid">
            {DIFFERENT.map((d) => (
              <article key={d.title} className="doc-card reveal">
                {icon(d.icon)}
                <h3>{d.title}</h3>
                <p>{d.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="doc-section" aria-labelledby="tech">
          <div className="reveal">
            <p className="doc-eyebrow">Technology</p>
            <h2 id="tech">What it is built with</h2>
          </div>
          <div className="doc-grid is-four">
            {TECH.map((t) => (
              <article key={t.group} className="doc-card reveal">
                <h3>{t.group}</h3>
                <ul className="doc-list">
                  {t.items.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="doc-disclaimer reveal" aria-labelledby="use">
          <p className="doc-hero-eyebrow">Intended use</p>
          <h2 id="use">A research prototype, not a medical device</h2>
          <p>
            <strong>
              CardioVanta is an educational and research prototype. It is not clinically validated and must not be used
              for diagnosis, treatment decisions or emergency medical decisions.
            </strong>
          </p>
          <p>
            It is meant for people studying calibrated and explainable machine learning: researchers, reviewers and
            students. If you are worried about your heart, speak to a doctor or call your local emergency number.
          </p>
        </section>

        <nav className="doc-section doc-next reveal" aria-label="Continue">
          <Link href="/research" transitionTypes={[NAV_LATERAL]}>
            <strong>Research &amp; Evidence</strong>
            <span>What has been measured, and its limits</span>
          </Link>
          <Link href="/assessment" transitionTypes={[NAV_LATERAL]}>
            <strong>Heart Analysis</strong>
            <span>The 13-input assessment</span>
          </Link>
          <Link href="/" transitionTypes={[NAV_BACK]}>
            <strong>Overview</strong>
            <span>Back to the home page</span>
          </Link>
        </nav>
      </div>
    </DocShell>
  );
}
