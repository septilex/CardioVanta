"use client";

/**
 * Evaluations recorded in the research database (GET /api/v1/research/evaluations, PostgreSQL JOINs).
 *
 * The data is loaded in a useEffect: fetching from the network is a side effect that must run after the page
 * renders, only in the browser, and be cancelled (AbortController) if the reader leaves before it finishes.
 */
import { useEffect, useState } from "react";
import { ApiError, fetchResearchEvaluations, type ResearchEvaluations } from "../../lib/api";
import { EvaluationsTable } from "./EvaluationsTable";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: ResearchEvaluations }
  | { kind: "unavailable"; message: string };

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

  return <EvaluationsTable data={state.data} />;
}
