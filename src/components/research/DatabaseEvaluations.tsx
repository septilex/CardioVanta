"use client";

/**
 * Evaluations recorded in the research database (GET /api/v1/research/evaluations, PostgreSQL JOINs).
 *
 * The data is loaded in a useEffect: fetching from the network is a side effect that must run after the page
 * renders, only in the browser, and be cancelled (AbortController) if the reader leaves before it finishes.
 */
import { useEffect, useState } from "react";
import { ApiError, fetchResearchEvaluations, type ResearchEvaluations } from "../../lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: ResearchEvaluations }
  | { kind: "unavailable"; message: string };

const METRIC_LABEL: Record<string, string> = {
  accuracy: "Accuracy",
  roc_auc: "ROC-AUC",
  sensitivity: "Sensitivity",
  specificity: "Specificity",
  calibration_slope: "Calibration slope",
  ece: "Calibration error (ECE)",
  brier: "Brier score",
};

export function DatabaseEvaluations() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchResearchEvaluations(controller.signal)
      .then((data) => {
        // A response that arrives after cleanup (unmount, or React Strict Mode's extra mount/unmount in
        // development) belongs to a discarded effect: never apply it.
        if (!controller.signal.aborted) setState({ kind: "ready", data });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return; // the reader left the page; nothing to show
        const message =
          err instanceof ApiError && err.code === "research_database_not_configured"
            ? "The research database is not connected in this environment."
            : "Research data could not be loaded right now.";
        setState({ kind: "unavailable", message });
      });
    return () => controller.abort();
  }, []);

  if (state.kind === "loading") {
    return <p className="doc-db-status" role="status">Loading evaluations from the research database…</p>;
  }
  if (state.kind === "unavailable") {
    return <p className="doc-db-status" role="status">{state.message}</p>;
  }

  const { evaluations, version_coverage, unevaluated_cohorts } = state.data;
  return (
    <div className="doc-db">
      <div className="doc-table-wrap">
        <table className="doc-table">
          <caption>
            Every recorded metric, joined to the model version and patient cohort it belongs to. Each row names the
            report it was copied from.
          </caption>
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th scope="col">Cohort</th>
              <th scope="col">Method</th>
              <th scope="col">Metric</th>
              <th scope="col" className="num">Value</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map((row) => (
              <tr key={`${row.version}-${row.cohort}-${row.method}-${row.metric}`}>
                <td>{row.version}</td>
                <td>
                  {row.cohort_name} <span className="range">n = {row.n_patients}</span>
                </td>
                <td>{row.method}</td>
                <th scope="row">{METRIC_LABEL[row.metric] ?? row.metric}</th>
                <td className="num">{row.value.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="doc-db-notes">
        {version_coverage
          .filter((v) => v.evaluation_count === 0)
          .map((v) => (
            <li key={v.version}>
              Model {v.version} has no evaluations of its own: it is a parameter-for-parameter export of an evaluated
              version ({v.serialization.replace("_", " ")}).
            </li>
          ))}
        {unevaluated_cohorts.length > 0 && (
          <li>
            Not yet evaluated with a registered model:{" "}
            {unevaluated_cohorts.map((c) => `${c.name} (${c.n_patients} patients)`).join(", ")}.
          </li>
        )}
      </ul>
    </div>
  );
}
