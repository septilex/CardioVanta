"use client";

import type { CSSProperties } from "react";
import type { PredictRequest } from "../../types";
import { CATEGORICAL_LABELS, FEATURE_METADATA, type CategoricalFeatureId } from "../../types/generated-features";

export interface OverviewStage {
  id: string;
  num: string;
  title: string;
  fieldKeys: (keyof PredictRequest)[];
}

interface StepsOverviewProps {
  stages: OverviewStage[];
  currentStage: number;
  formData: PredictRequest;
  onJump: (idx: number) => void;
}

/** A recorded value as people read it: categorical codes by their contract label, numbers with units. */
function display(key: keyof PredictRequest, value: number): string {
  const labels = (CATEGORICAL_LABELS as Record<string, Readonly<Record<number, string>> | undefined>)[key as CategoricalFeatureId];
  if (labels) return labels[value] ?? String(value);
  if (!Number.isFinite(value)) return "—";
  const unit = FEATURE_METADATA[key].unit;
  return unit ? `${value} ${unit}` : String(value);
}

/**
 * The whole assessment at a glance, filling the space below the form card: completed steps show what
 * was recorded, the current step is highlighted, upcoming steps list their fields and units.
 * Every card opens its step. Field names, units and code labels come from the feature contract.
 */
export default function StepsOverview({ stages, currentStage, formData, onJump }: StepsOverviewProps) {
  const done = stages.slice(0, currentStage).reduce((n, s) => n + s.fieldKeys.length, 0);
  const total = stages.reduce((n, s) => n + s.fieldKeys.length, 0);

  return (
    <section className="ax-journey" aria-labelledby="ax-journey-title">
      <header className="ax-journey-head">
        <h2 id="ax-journey-title" className="ax-journey-title">Your assessment at a glance</h2>
        <span className="ax-journey-meta">
          {done} of {total} inputs confirmed · {(() => { const left = stages.length - currentStage - 1; return left === 0 ? "last step" : `${left} ${left === 1 ? "step" : "steps"} after this one`; })()}
        </span>
      </header>

      <ol className="ax-journey-grid">
        {stages.map((stage, idx) => {
          const state = idx < currentStage ? "done" : idx === currentStage ? "current" : "next";
          return (
            <li key={stage.id} style={{ "--i": idx } as CSSProperties}>
              <button
                type="button"
                className="ax-journey-card"
                data-state={state}
                onClick={() => onJump(idx)}
                aria-current={state === "current" ? "step" : undefined}
                aria-label={`Open step ${idx + 1}: ${stage.title}`}
              >
                <span className="ax-journey-top">
                  <span className="ax-journey-num">{stage.num}</span>
                  <span className="ax-journey-state">
                    {state === "done" ? "Recorded" : state === "current" ? "In progress" : `${stage.fieldKeys.length} fields`}
                  </span>
                </span>
                <span className="ax-journey-name">{stage.title}</span>
                {/* One-line version for when the panel has less height (see assessment.css). */}
                <span className="ax-journey-summary">
                  {stage.fieldKeys
                    .map((key) => (state === "next" ? FEATURE_METADATA[key].label : display(key, formData[key] as number)))
                    .join(" · ")}
                </span>
                <span className="ax-journey-fields">
                  {stage.fieldKeys.map((key) => (
                    <span key={key} className="ax-journey-field">
                      <span className="ax-journey-label">{FEATURE_METADATA[key].label}</span>
                      <span className="ax-journey-value">
                        {state === "next" ? FEATURE_METADATA[key].unit ?? "choice" : display(key, formData[key] as number)}
                      </span>
                    </span>
                  ))}
                </span>
                <span className="ax-journey-go" aria-hidden="true">
                  {state === "done" ? "Review" : state === "current" ? "You are here" : "Go to step"} <span className="ax-btn-arrow">→</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
