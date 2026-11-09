"use client";

import React from "react";
import type { PredictRequest } from "../../types";
import { FEATURE_METADATA } from "../../types/generated-features";

export interface StripStage {
  num: string;
  title: string;
  fieldKeys: (keyof PredictRequest)[];
}

interface NextStepStripProps {
  stages: StripStage[];
  currentStage: number;
  hasResult: boolean;
  onViewResult: () => void;
}

/**
 * One-line "up next" hint that sits between the Previous and Continue buttons.
 * Field names come from the generated feature contract so they match the form.
 */
export default function NextStepStrip({ stages, currentStage, hasResult, onViewResult }: NextStepStripProps) {
  const next = stages[currentStage + 1];

  if (!next) {
    const total = stages.reduce((n, s) => n + s.fieldKeys.length, 0);
    return (
      <div className="ax-strip ax-strip--ready">
        <span className="ax-strip-mark" aria-hidden="true">✓</span>
        <span className="ax-strip-text">All {total} inputs ready</span>
        {hasResult && (
          <button type="button" className="ax-strip-link" onClick={onViewResult}>
            View last result →
          </button>
        )}
      </div>
    );
  }

  const fields = next.fieldKeys.map((k) => FEATURE_METADATA[k].label).join(" · ");
  const laterSteps = stages.length - currentStage - 2;

  return (
    <div className="ax-strip" title={`${next.title}: ${fields}`}>
      <span className="ax-strip-tag">Up next</span>
      <span className="ax-strip-text">
        <span className="ax-strip-step">
          {next.num} {next.title}
        </span>
        <span className="ax-strip-fields">{fields}</span>
      </span>
      {laterSteps > 0 && (
        <span className="ax-strip-more">+{laterSteps} more</span>
      )}
    </div>
  );
}
