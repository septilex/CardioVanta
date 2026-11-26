"use client";

/**
 * "Was this explanation helpful?" under the result. Creates, changes and withdraws one anonymous MongoDB document
 * (POST, PATCH, DELETE /api/v1/feedback). The edit token returned at creation stays in this component's memory
 * only, so the feedback can be changed or withdrawn until the person leaves the result.
 */
import { useRef, useState } from "react";
import { ApiError, createFeedback, deleteFeedback, updateFeedback, type FeedbackSection } from "../../lib/api";

type State =
  | { kind: "idle"; note?: string }
  | { kind: "saving" }
  | { kind: "saved"; helpful: boolean }
  | { kind: "unavailable" };

export default function ExplanationFeedback({ section, modelVersion }: { section: FeedbackSection; modelVersion: string }) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const saved = useRef<{ id: string; token: string } | null>(null);

  const fail = (err: unknown) => {
    const notConfigured = err instanceof ApiError && err.status === 503;
    setState(notConfigured ? { kind: "unavailable" } : { kind: "idle", note: "That didn't save. Please try again." });
  };

  const vote = async (helpful: boolean) => {
    setState({ kind: "saving" });
    try {
      if (saved.current) {
        await updateFeedback(saved.current.id, saved.current.token, helpful);
      } else {
        const created = await createFeedback(helpful, section, modelVersion);
        saved.current = { id: created.id, token: created.edit_token };
      }
      setState({ kind: "saved", helpful });
    } catch (err) {
      fail(err);
    }
  };

  const withdraw = async () => {
    if (!saved.current) return;
    setState({ kind: "saving" });
    try {
      await deleteFeedback(saved.current.id, saved.current.token);
      saved.current = null;
      setState({ kind: "idle", note: "Your feedback was removed." });
    } catch (err) {
      fail(err);
    }
  };

  if (state.kind === "unavailable") {
    return <p className="ax-feedback ax-feedback--note" role="status">Feedback isn&rsquo;t available right now.</p>;
  }

  const busy = state.kind === "saving";
  return (
    <div className="ax-feedback" role="group" aria-label="Explanation feedback">
      {state.kind === "saved" ? (
        <>
          <span className="ax-feedback-q" role="status">
            Thanks. You marked this explanation as {state.helpful ? "helpful" : "not helpful"}.
          </span>
          <button type="button" className="ax-feedback-btn" onClick={() => void vote(!state.helpful)}>
            Change to {state.helpful ? "not helpful" : "helpful"}
          </button>
          <button type="button" className="ax-feedback-btn ax-feedback-btn--quiet" onClick={() => void withdraw()}>
            Remove my feedback
          </button>
        </>
      ) : (
        <>
          <span className="ax-feedback-q">Was this explanation helpful?</span>
          <button type="button" className="ax-feedback-btn" disabled={busy} onClick={() => void vote(true)}>Yes</button>
          <button type="button" className="ax-feedback-btn" disabled={busy} onClick={() => void vote(false)}>No</button>
          {state.kind === "idle" && state.note && <span className="ax-feedback-note" role="status">{state.note}</span>}
        </>
      )}
      <span className="ax-feedback-fine">Anonymous. Only your answer, the tab and the model version are stored.</span>
    </div>
  );
}
