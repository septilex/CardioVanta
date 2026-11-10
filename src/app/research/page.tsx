import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import { DocShell } from "../../components/shell/DocShell";
import { CountUp } from "../../components/motion/CountUp";
import { NAV_BACK, NAV_LATERAL } from "../../lib/motion";

export const metadata: Metadata = {
  title: "Research & Evidence | CardioVanta",
  description:
    "What CardioVanta has investigated, measured and established about its cardiovascular risk model, with sources.",
};

/** Every source below is a tracked file on the project's GitHub branch. */
const REPO = "https://github.com/septilex/CardioVanta/blob/horizon0/research-ci-quarantine";

const order = (i: number) => ({ "--cv-i": i }) as CSSProperties;

type Status = "done" | "no" | "open" | "info";
const STATUS_LABEL: Record<Status, string> = { done: "Adopted", no: "Not adopted", open: "Unresolved", info: "Finding" };

interface Milestone {
  date: string;
  title: string;
  status: Status;
  label?: string;
  body: ReactNode;
}

const ERAS: { name: string; items: Milestone[] }[] = [
  {
    name: "Foundations",
    items: [
      {
        date: "2 Oct 2026",
        title: "Training provenance and artifact integrity",
        status: "done",
        body: (
          <>
            Model metadata records the data hashes, random seed and Git commit used for training, and a SHA-256
            manifest of the model files is checked in CI (<code>5073e22</code>, <code>a1cf0a3</code>).
          </>
        ),
      },
      {
        date: "6 Oct 2026",
        title: "Nested cross-validation correction",
        status: "done",
        body: (
          <>
            Model selection was moved inside a global nested cross-validation, with a dedicated leakage test (
            <code>006d7fe</code>).
          </>
        ),
      },
      {
        date: "19 Oct 2026",
        title: "Phase 16: feature engineering",
        status: "no",
        body: <>Alternative feature representations were evaluated. The recorded decision was to keep the frozen baseline.</>,
      },
      {
        date: "21 Oct 2026",
        title: "Phase 17: leave-one-cohort-out validation",
        status: "info",
        label: "Discovery",
        body: (
          <>
            Work with the Hungarian and Long Beach cohorts and the UCI codebook revealed that the training target was
            inverted and that chest-pain codes had been recoded. Both were corrected in the next era.
          </>
        ),
      },
    ],
  },
  {
    name: "Foundation rebuild · 31 Oct 2026",
    items: [
      {
        date: "R0.3",
        title: "Outcome orientation correction",
        status: "done",
        body: (
          <>
            The model&apos;s probability column had meant <em>no</em> disease: a textbook high-risk profile scored 1.4%.
            Disease orientation is now declared per model and mapped explicitly, and chest-pain labels were corrected.
          </>
        ),
      },
      {
        date: "R1",
        title: "Unified clinical feature contract",
        status: "done",
        body: (
          <>
            One JSON contract (v2.0.0) defines the 13 inputs, codes, units, ranges and per-code evidence. Python and
            TypeScript definitions are generated from it, and CI rejects stale generated code.
          </>
        ),
      },
      {
        date: "R2",
        title: "Model registry and artifact verification",
        status: "done",
        body: (
          <>
            The <code>cardiovanta_ml</code> package loads an explicitly versioned model and verifies every file&apos;s
            SHA-256 before deserialising it. Any mismatch stops the service from starting.
          </>
        ),
      },
      {
        date: "R3",
        title: "Runtime and CI hardening",
        status: "done",
        body: <>Python 3.12, a pinned numerical stack, a clean-install check of the model package and a restructured CI.</>,
      },
    ],
  },
  {
    name: "Pre-registered studies · 31 Oct – 1 Nov 2026",
    items: [
      {
        date: "R4",
        title: "Count encoding of major vessels (ca)",
        status: "no",
        body: <>Treating <code>ca</code> as a count did not improve calibration or stability. The production encoding was kept.</>,
      },
      {
        date: "H2",
        title: "Calibration of the training recipe",
        status: "info",
        body: (
          <>
            Found that the production recipe is under-confident (calibration slope about 1.29). Pooled out-of-fold
            calibration brought it to about 1.02 in 10 of 10 repeats; class weighting had no effect.
          </>
        ),
      },
      {
        date: "H2.1",
        title: "Calibration confirmation",
        status: "done",
        label: "Confirmed",
        body: (
          <>
            On 20 new partitions, pooled out-of-fold calibration moved the slope from 1.267 to 1.003 with no loss of
            discrimination; all four pre-registered criteria passed. Production is unchanged until a new model version
            is approved.
          </>
        ),
      },
      {
        date: "R5",
        title: "Explanation stability",
        status: "info",
        body: (
          <>
            Across 3,562 single-feature changes to 100 synthetic profiles, the explanation always moved in the same
            direction as the probability. Instability concentrates on inputs whose codes have no established meaning.
          </>
        ),
      },
      {
        date: "R6",
        title: "Feature codebook resolution",
        status: "open",
        body: (
          <>
            The meanings of <code>slope</code>, <code>thal</code>, <code>ca = 4</code> and <code>thal = 0</code> could
            not be verified from available records. No clinical meaning is assigned to them.
          </>
        ),
      },
      {
        date: "R7",
        title: "Unverified feature ablation",
        status: "info",
        body: (
          <>
            The recipe depends materially on <code>ca</code> and <code>thal</code> and barely on <code>slope</code>.
            Removing all three lowered ROC-AUC from 0.913 to 0.877.
          </>
        ),
      },
    ],
  },
  {
    name: "Operations · Nov 2026",
    items: [
      {
        date: "1 Nov 2026",
        title: "Research-data quarantine in CI",
        status: "done",
        body: <>Protected research data is kept off CI runners, and any attempt to read it fails the build.</>,
      },
      {
        date: "3 Nov 2026",
        title: "Production verification",
        status: "open",
        label: "Open blocker",
        body: <>A read-only check confirmed that the live deployment still serves the inverted, pre-correction output.</>,
      },
      {
        date: "4 Nov 2026",
        title: "Prediction containment",
        status: "done",
        body: <>Predictions are switched off by a committed setting until corrected serving code is verified in production.</>,
      },
    ],
  },
];

interface MetricRow {
  name: string;
  production: string;
  range?: string;
  pooled: string;
  meaning: string;
  limit: string;
}

const METRICS: MetricRow[] = [
  {
    name: "ROC-AUC",
    production: "0.911",
    range: "0.904–0.919",
    pooled: "0.911",
    meaning: "How well the model ranks a patient with disease above one without (1 is perfect, 0.5 is chance).",
    limit: "Ranking only: a model can rank well and still give wrong-sized probabilities.",
  },
  {
    name: "Log loss",
    production: "0.380",
    pooled: "0.374",
    meaning: "Penalises probabilities that are confidently wrong. Lower is better.",
    limit: "Depends on how common the disease is in this cohort.",
  },
  {
    name: "Brier score",
    production: "0.117",
    pooled: "0.116",
    meaning: "Mean squared gap between the probability and what happened. Lower is better.",
    limit: "Mixes ranking and calibration; also depends on prevalence.",
  },
  {
    name: "Calibration slope",
    production: "1.267",
    range: "1.169–1.374",
    pooled: "1.003",
    meaning: "1 is ideal. Above 1 means the probabilities are too timid, pulled towards 50%.",
    limit: "The deployed recipe is under-confident; the confirmed fix is not deployed.",
  },
  {
    name: "Expected calibration error",
    production: "0.059",
    pooled: "0.040",
    meaning: "Average gap between predicted and observed frequency across 10 probability bins.",
    limit: "Sensitive to binning with only 242 patients.",
  },
];

const DOCS: { href: string; title: string; note: string }[] = [
  { href: "reports/h2_1_calibration_confirmation.md", title: "H2.1 Calibration confirmation", note: "Source of the evaluation table" },
  { href: "reports/h2_calibration_recipe.md", title: "H2 Calibration recipe", note: "Under-confidence finding" },
  { href: "reports/r4_ca_count_encoding.md", title: "R4 Count encoding of ca", note: "Pre-registered, not supported" },
  { href: "reports/r5_explanation_stability.md", title: "R5 Explanation stability", note: "3,562 synthetic perturbations" },
  { href: "reports/r6_feature_codebook_resolution.md", title: "R6 Codebook resolution", note: "Unresolved feature codes" },
  { href: "reports/r7_unverified_feature_ablation.md", title: "R7 Unverified feature ablation", note: "Dependence on ca, thal, slope" },
  { href: "reports/phase17_multicenter_validation.md", title: "Phase 17 Multicenter validation", note: "Cross-cohort research" },
  { href: "artifacts/models/cardiovanta-lr13/1.0.0/model_card.md", title: "Model card: cardiovanta-lr13 1.0.0", note: "The deployed model" },
  { href: "cardiovanta_ml/contracts/feature_schema.v2.json", title: "Clinical feature contract v2.0.0", note: "Inputs, codes and evidence levels" },
  { href: "docs/reports/PRODUCTION_VERIFICATION_2026-11-03.md", title: "Production verification", note: "3 Nov 2026 blocker" },
  { href: "docs/reports/PREDICTION_CONTAINMENT_2026-11-04.md", title: "Prediction containment", note: "Why predictions are paused" },
  { href: "docs/reports/CARDIOVANTA_ULTIMATE_MASTER_ENGINEERING_REPORT.md", title: "Master engineering report", note: "Full history and evidence levels" },
];

export default function ResearchPage() {
  return (
    <DocShell section="Research">
      <section className="doc-hero" aria-labelledby="research-title">
        <div className="doc-hero-inner">
          <p className="doc-hero-eyebrow cv-rise" style={order(0)}>Research · model cardiovanta-lr13 1.0.0</p>
          <h1 id="research-title" className="cv-rise" style={order(1)}>Research &amp; Evidence</h1>
          <p className="doc-hero-lede cv-rise" style={order(2)}>
            What CardioVanta has investigated, measured and established about its cardiovascular machine-learning
            model, and where the evidence stops. Every figure on this page links back to a report in the repository.
          </p>
          <ul className="doc-hero-facts cv-rise" style={order(3)} aria-label="Key facts">
            <li><CountUp value="242" /> development patients</li>
            <li><CountUp value="13" /> clinical inputs</li>
            <li>Pre-registered studies R4–R7, H2, H2.1</li>
            <li>No external validation of this model</li>
          </ul>
        </div>
      </section>

      <div className="doc-body">
        <section className="doc-section reveal" aria-labelledby="overview">
          <p className="doc-eyebrow">Research overview</p>
          <h2 id="overview">An auditable model, not a black box</h2>
          <div className="doc-grid">
            <article className="doc-card">
              <h3>Objective</h3>
              <p>
                Estimate the probability of significant obstructive coronary artery disease from 13 structured
                measurements, as an auditable reference for calibrated and interpretable cardiovascular machine learning.
              </p>
            </article>
            <article className="doc-card">
              <h3>Modelling approach</h3>
              <p>
                L2-regularised logistic regression (C = 0.1, class-balanced) with scaled continuous inputs and one-hot
                categorical inputs, sigmoid-calibrated as five averaged members. Fitted on 242 development rows of the
                Kaggle redistribution of the UCI Cleveland data.
              </p>
            </article>
            <article className="doc-card">
              <h3>Evaluation philosophy</h3>
              <p>
                Designs are written and hashed before any code runs, failures are recorded as carefully as successes, and
                splits keep duplicate patients together. The 61 locked rows are never read by these studies.
              </p>
            </article>
          </div>
        </section>

        <section className="doc-section" aria-labelledby="milestones">
          <div className="reveal">
            <p className="doc-eyebrow">Research milestones</p>
            <h2 id="milestones">What has been done, in order</h2>
          </div>
          <div className="doc-eras">
            {ERAS.map((era, e) => (
              <div key={era.name} className="doc-era-block">
                <p className="doc-era reveal" id={`era-${e}`}>{era.name}</p>
                <ol className="doc-timeline" aria-labelledby={`era-${e}`}>
                  {era.items.map((m) => (
                    <li key={m.title} className="reveal">
                      <div className="doc-timeline-head">
                        <span className="doc-date">{m.date}</span>
                        <span className={`doc-tag is-${m.status}`}>{m.label ?? STATUS_LABEL[m.status]}</span>
                      </div>
                      <h3>{m.title}</h3>
                      <p>{m.body}</p>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </section>

        <section className="doc-section" aria-labelledby="evaluation">
          <div className="reveal">
            <p className="doc-eyebrow">Model evaluation</p>
            <h2 id="evaluation">How the training recipe performs on its own data</h2>
          </div>
          <div className="doc-table-wrap reveal">
            <table className="doc-table">
              <caption>
                Mean over 20 repeats of 5-fold nested, duplicate-aware cross-validation on the 242-patient development
                cohort (H2.1). Ranges are the 2.5–97.5th percentiles across repeats.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col" className="num">Production recipe</th>
                  <th scope="col" className="num">Pooled calibration (not deployed)</th>
                  <th scope="col">What it tells you · and its limit</th>
                </tr>
              </thead>
              <tbody>
                {METRICS.map((m) => (
                  <tr key={m.name}>
                    <th scope="row">{m.name}</th>
                    <td className="num">
                      <CountUp value={m.production} />
                      {m.range && <span className="range">{m.range}</span>}
                    </td>
                    <td className="num"><CountUp value={m.pooled} /></td>
                    <td>
                      {m.meaning} <strong>Limit:</strong> {m.limit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="doc-callout reveal">
            <p>
              <strong>These are development-cohort results, not external validation.</strong> They describe how the
              training recipe behaves on the same 242 historical patients it learns from, re-split many times. They are
              not evidence of clinical accuracy for any other population.
            </p>
          </div>
        </section>

        <section className="doc-section" aria-labelledby="explain">
          <div className="reveal">
            <p className="doc-eyebrow">Explainability and calibration</p>
            <h2 id="explain">Reading a probability and its explanation</h2>
          </div>
          <div className="doc-grid is-four">
            <article className="doc-card reveal">
              <h3>Why calibration matters</h3>
              <p>
                A calibrated 30% should mean that about 30 in 100 similar patients had the disease. Without calibration a
                number can rank patients well and still overstate or understate their risk.
              </p>
            </article>
            <article className="doc-card reveal">
              <h3>How the estimate is produced</h3>
              <p>
                The 13 inputs are validated against the contract, transformed, and scored by five calibrated logistic
                models whose probabilities are averaged. The disease-present label is declared in the model&apos;s
                metadata, not assumed.
              </p>
            </article>
            <article className="doc-card reveal">
              <h3>What the explanations show</h3>
              <p>
                Two additive breakdowns (linear contributions and a SHAP-equivalent view) of a separate, uncalibrated
                explanation model. They show direction and relative weight; they do not exactly decompose the calibrated
                probability.
              </p>
            </article>
            <article className="doc-card reveal">
              <h3>Why they are not causes</h3>
              <p>
                They describe statistical association in historical records. A feature pushing the estimate up is not
                evidence that it causes disease, and inputs with unverified codes carry no clinical meaning here.
              </p>
            </article>
          </div>
        </section>

        <section className="doc-section" aria-labelledby="limits">
          <div className="reveal">
            <p className="doc-eyebrow">Research limitations</p>
            <h2 id="limits">Where the evidence stops</h2>
          </div>
          <div className="doc-grid is-four">
            <article className="doc-card reveal">
              <span className="doc-tag is-open">Cohort</span>
              <h3>A small historical cohort</h3>
              <p>242 development rows from a public redistribution of 1980s Cleveland records, with duplicate patients.</p>
            </article>
            <article className="doc-card reveal">
              <span className="doc-tag is-open">Validation</span>
              <h3>No external clinical validation</h3>
              <p>
                The 13-feature model has not been validated on an independent population. The locked test rows are no
                longer independent of earlier work.
              </p>
            </article>
            <article className="doc-card reveal">
              <span className="doc-tag is-open">Features</span>
              <h3>Unresolved feature codes</h3>
              <p>
                The meanings of <code>slope</code>, <code>thal</code>, <code>ca = 4</code> and <code>thal = 0</code> remain
                unverified (R6), and the model depends on two of them (R7).
              </p>
            </article>
            <article className="doc-card reveal">
              <span className="doc-tag is-open">Calibration</span>
              <h3>Calibration and generalisation</h3>
              <p>
                The deployed recipe is under-confident (slope about 1.27). The confirmed fix is not yet in a released
                model, and calibration on other populations is unknown.
              </p>
            </article>
          </div>
          <div className="doc-callout reveal">
            <p>
              <strong>Not a diagnostic tool.</strong> CardioVanta must not be used to diagnose, treat or triage anyone.
              Predictions are currently paused in deployment while the prediction service is verified.
            </p>
          </div>
        </section>

        <section className="doc-section" aria-labelledby="docs">
          <div className="reveal">
            <p className="doc-eyebrow">Research documentation</p>
            <h2 id="docs">Read the sources</h2>
            <p className="doc-prose">Reports open on GitHub in a new tab.</p>
          </div>
          <ul className="doc-links">
            {DOCS.map((d) => (
              <li key={d.href} className="reveal">
                <a href={`${REPO}/${d.href}`} target="_blank" rel="noopener noreferrer">
                  <strong>{d.title}</strong>
                  <span>{d.note}</span>
                  <span className="doc-arrow" aria-hidden="true">↗</span>
                </a>
              </li>
            ))}
          </ul>
        </section>

        <nav className="doc-section doc-next reveal" aria-label="Continue">
          <Link href="/about" transitionTypes={[NAV_LATERAL]}>
            <strong>About CardioVanta</strong>
            <span>What the platform is and how it works</span>
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
