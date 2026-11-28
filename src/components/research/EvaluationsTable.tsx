/**
 * The research-database evaluations table. Presentational only (no hooks, no "use client"), so it renders in a
 * Server Component (the request-time page at /research/evaluations) and inside the browser-fetched
 * DatabaseEvaluations on /research alike: one table, two data-loading strategies.
 */
import type { ResearchEvaluations } from "../../lib/api";

const METRIC_LABEL: Record<string, string> = {
  accuracy: "Accuracy",
  roc_auc: "ROC-AUC",
  sensitivity: "Sensitivity",
  specificity: "Specificity",
  calibration_slope: "Calibration slope",
  ece: "Calibration error (ECE)",
  brier: "Brier score",
  log_loss: "Log loss",
};

export function EvaluationsTable({ data }: { data: ResearchEvaluations }) {
  const { evaluations, version_coverage, unevaluated_cohorts } = data;
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
