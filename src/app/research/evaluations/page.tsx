import Link from "next/link";
import type { Metadata } from "next";
import { DocShell } from "../../../components/shell/DocShell";
import { EvaluationsTable } from "../../../components/research/EvaluationsTable";
import { loadEvaluationsOnServer } from "../../../lib/serverResearch";

/*
 * Server-side rendering (request time). This page is rendered on the server for EVERY request: it reads the live
 * research database through the API and sends finished HTML, so the table is present with JavaScript disabled and
 * reflects an import immediately. Contrast /research, which is prerendered once at build time and loads the same
 * table in the browser (DatabaseEvaluations, useEffect).
 */
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Recorded evaluations | CardioVanta",
  description: "Every research evaluation recorded in the CardioVanta research database, rendered on the server per request.",
};

export default async function ResearchEvaluationsPage() {
  const result = await loadEvaluationsOnServer();
  const renderedAt = new Date().toISOString();
  return (
    <DocShell section="Research">
      <section className="doc-section" aria-labelledby="evaluations-title">
        <div>
          <p className="doc-eyebrow">Research database</p>
          <h1 id="evaluations-title">Recorded evaluations</h1>
          <p>
            Rendered on the server for this request at <time dateTime={renderedAt}>{renderedAt}</time>. Reload to render
            again; a new research import appears here immediately.
          </p>
        </div>
        {result.kind === "ready" ? (
          <EvaluationsTable data={result.data} />
        ) : (
          <p className="doc-db-status" role="status">{result.message}</p>
        )}
        <p>
          <Link href="/research">Back to Research &amp; Evidence</Link>
        </p>
      </section>
    </DocShell>
  );
}
