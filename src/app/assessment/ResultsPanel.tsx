"use client";

import { useLayoutEffect, useRef, type CSSProperties, type KeyboardEvent } from "react";
import { m, useReducedMotion } from "framer-motion";
import type { PredictResponse } from "../../types";
import { AnimatedNumber } from "../../components/motion/AnimatedNumber";
import {
  TRANSITION,
  formatProbability,
  panelSwap,
  revealGroup,
  revealItem,
} from "../../lib/motion";

export type ResultTab = "summary" | "why" | "audit";

/** Seconds after the panel arrives before the gauge and count-up start. */
const COUNT_DELAY = 0.25;

/** Per-frame formatter for the count-up; module-level so its identity never changes. */
const formatPercentFrame = (n: number) => n.toFixed(1);

const cx = (...names: (string | false | undefined)[]) => names.filter(Boolean).join(" ");

// Human-readable threshold status. The API's class is disease-positive:
// class 1 = P(CAD present) >= threshold, class 0 = below it. Unknown statuses fall back to the raw text.
export function describeThreshold(prediction: PredictResponse["prediction"] | undefined): string {
  if (!prediction || !prediction.threshold_status) {
    return "No validated decision threshold is configured. Probability only.";
  }
  if (prediction.threshold_status === "no_validated_production_threshold_configured") {
    return "No validated decision threshold is configured. Probability only.";
  }
  if (prediction.threshold_status === "mathematical_model_operating_point" && prediction.threshold_applied != null) {
    const pct = (prediction.threshold_applied * 100).toFixed(0);
    return prediction.class === 1
      ? `At or above the ${pct}% operating point: classified as CAD present (mathematical operating point, not a diagnosis).`
      : `Below the ${pct}% operating point: classified as CAD absent (mathematical operating point, not a diagnosis).`;
  }
  return prediction.threshold_status;
}

interface ResultsPanelProps {
  result: PredictResponse;
  tab: ResultTab;
  onTabChange: (tab: ResultTab) => void;
  onEdit: () => void;
  onNew: () => void;
}

/**
 * The analysis view that replaces the form card. Every value shown is read from `result`;
 * the animations only change how those values arrive, never what they are.
 */
export function ResultsPanel({ result, tab, onTabChange, onEdit, onNew }: ResultsPanelProps) {
  const tabs = (
    [
      ["summary", "Result", true],
      ["why", "Why", !!result.shap_equivalent_explanation],
      ["audit", "Technical audit", !!result.explanation],
    ] as const
  ).filter(([, , show]) => show);

  return (
    <m.section
      id="result-section"
      className="ax-results-panel"
      aria-label="Analysis results"
      variants={panelSwap}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <div className="ax-results-head">
        <button type="button" className="ax-results-back" onClick={onEdit}>
          <span className="ax-btn-arrow ax-btn-arrow--back" aria-hidden="true">←</span> Edit inputs
        </button>
        <ResultTabs tabs={tabs.map(([id, label]) => [id, label] as const)} active={tab} onChange={onTabChange} />
        <button type="button" className="ax-results-new" onClick={onNew}>
          New assessment
        </button>
      </div>

      <div className="ax-results-body">
        <SummaryPanel result={result} active={tab === "summary"} />
        {result.shap_equivalent_explanation && (
          <WhyPanel shap={result.shap_equivalent_explanation} active={tab === "why"} />
        )}
        {result.explanation && <AuditPanel explanation={result.explanation} active={tab === "audit"} />}
      </div>
    </m.section>
  );
}

/* ─── Tabs: roving tab index, arrow-key navigation, sliding indicator ─────────────────── */

function ResultTabs({
  tabs,
  active,
  onChange,
}: {
  tabs: (readonly [ResultTab, string])[];
  active: ResultTab;
  onChange: (tab: ResultTab) => void;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const indicatorRef = useRef<HTMLSpanElement>(null);

  // Position the indicator under the active tab. Written straight to the element (no state), and
  // re-measured when the tab list resizes (web fonts loading, window resizing).
  useLayoutEffect(() => {
    const list = listRef.current;
    const indicator = indicatorRef.current;
    if (!list || !indicator) return;
    const place = () => {
      const el = list.querySelector<HTMLElement>(`[data-tab="${active}"]`);
      if (!el) return;
      indicator.style.width = `${el.offsetWidth}px`;
      indicator.style.transform = `translateX(${el.offsetLeft}px)`;
      indicator.dataset.ready = "true";
    };
    place();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(place);
    observer.observe(list);
    return () => observer.disconnect();
  }, [active]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const ids = tabs.map(([id]) => id);
    const index = ids.indexOf(active);
    let next: ResultTab | undefined;
    if (e.key === "ArrowRight") next = ids[(index + 1) % ids.length];
    else if (e.key === "ArrowLeft") next = ids[(index - 1 + ids.length) % ids.length];
    else if (e.key === "Home") next = ids[0];
    else if (e.key === "End") next = ids[ids.length - 1];
    if (!next) return;
    e.preventDefault();
    onChange(next);
    listRef.current?.querySelector<HTMLElement>(`[data-tab="${next}"]`)?.focus();
  };

  return (
    <div className="ax-results-tabs" role="tablist" aria-label="Result views" ref={listRef} onKeyDown={onKeyDown}>
      <span className="ax-results-tab-indicator" ref={indicatorRef} aria-hidden="true" />
      {tabs.map(([id, label]) => (
        <button
          key={id}
          type="button"
          role="tab"
          id={`ax-tab-${id}`}
          data-tab={id}
          aria-selected={active === id}
          aria-controls={`ax-tabpanel-${id}`}
          tabIndex={active === id ? 0 : -1}
          className="ax-results-tab"
          onClick={() => onChange(id)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/* ─── Result: gauge, count-up and the threshold statement ─────────────────────────────── */

function SummaryPanel({ result, active }: { result: PredictResponse; active: boolean }) {
  const probability = result.prediction?.probability;
  const percentText = probability != null ? formatProbability(probability) : "--";

  return (
    <div
      role="tabpanel"
      id="ax-tabpanel-summary"
      aria-labelledby="ax-tab-summary"
      hidden={!active}
      className={cx("ax-result-section", "ax-tabpanel", !active && "ax-stage-hidden")}
    >
      <m.div className="ax-result-container" variants={revealGroup} initial="hidden" animate="visible">
        <m.div className="ax-result-prob-block" variants={revealItem}>
          <div className="ax-gauge-wrap">
          {probability != null && <ProbabilityGauge probability={probability} />}
          <div className="ax-result-prob-val">
            {probability != null ? (
              <>
                <AnimatedNumber
                  className="ax-prob-number"
                  value={probability * 100}
                  format={formatPercentFrame}
                  delay={COUNT_DELAY}
                />
                <span className="ax-prob-unit" aria-hidden="true">%</span>
                <span className="sr-only">{percentText}%</span>
              </>
            ) : (
              <>
                --<span className="ax-prob-unit">%</span>
              </>
            )}
          </div>
          </div>
          <div className="ax-result-label">Modelled probability of significant obstructive CAD</div>
        </m.div>
        <div>
          <m.div className="ax-result-info" variants={revealItem}>
            Based on the provided profile, the research model estimates a{" "}
            <strong>{percentText}%</strong> probability that significant obstructive coronary artery disease is present. This is a research estimate, not a diagnosis, and the model is not clinically validated.
          </m.div>
          <m.div className="ax-result-threshold" variants={revealItem}>
            <strong>{describeThreshold(result.prediction)}</strong>
          </m.div>
          {result.development_range_warning?.outside_development_range && (
            <m.div className="ax-warning" variants={revealItem}>
              <strong>Development Range Guardrail:</strong> Features outside observed development-data range:{" "}
              {(result.development_range_warning.features || []).join(", ")}.
            </m.div>
          )}
        </div>
      </m.div>
    </div>
  );
}

/**
 * A ring whose filled share equals the returned probability. One colour regardless of value:
 * no validated decision threshold exists, so the gauge must not suggest risk bands.
 */
function ProbabilityGauge({ probability }: { probability: number }) {
  const reduce = useReducedMotion();
  const share = Math.min(1, Math.max(0, probability));
  return (
    <svg className="ax-gauge" viewBox="0 0 120 120" aria-hidden="true" focusable="false">
      <circle className="ax-gauge-track" cx="60" cy="60" r="52" />
      <m.circle
        className="ax-gauge-fill"
        cx="60"
        cy="60"
        r="52"
        initial={{ pathLength: reduce ? share : 0 }}
        animate={{ pathLength: share }}
        transition={reduce ? { duration: 0 } : { ...TRANSITION.count, delay: COUNT_DELAY }}
      />
    </svg>
  );
}

/* ─── Why: attribution bars that grow to their real length ────────────────────────────── */

function WhyPanel({
  shap,
  active,
}: {
  shap: NonNullable<PredictResponse["shap_equivalent_explanation"]>;
  active: boolean;
}) {
  const contributionsArray = Object.entries(shap.contributions) as [string, number][];
  const increasing = contributionsArray.filter(([, val]) => val > 0).sort((a, b) => b[1] - a[1]);
  const decreasing = contributionsArray.filter(([, val]) => val <= 0).sort((a, b) => a[1] - b[1]);
  const maxAbsValue = Math.max(...contributionsArray.map(([, val]) => Math.abs(val)), 1);

  const renderBar = (feature: string, value: number, isPos: boolean, index: number) => {
    const pct = Math.min(100, Math.round((Math.abs(value) / maxAbsValue) * 100));
    return (
      <div key={feature} style={{ display: "flex", alignItems: "center", marginBottom: "12px" }}>
        <div style={{ flex: "0 1 110px", minWidth: "80px", fontWeight: 600, fontSize: "13px", color: "var(--ax-text-main)", textTransform: "capitalize", wordBreak: "break-word", lineHeight: 1.2 }}>
          {feature}
        </div>
        <div role="progressbar" aria-label={`${feature} contribution: ${value.toFixed(3)}`} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} style={{ flex: "1 1 50px", height: "8px", backgroundColor: "#EAE3DC", borderRadius: "4px", overflow: "hidden", margin: "0 16px" }}>
          <div
            className="ax-bar-fill"
            style={{ width: `${pct}%`, height: "100%", backgroundColor: isPos ? "#9E1B2E" : "#4A72C8", borderRadius: "4px", "--i": index } as CSSProperties}
          />
        </div>
        <div style={{ flex: "0 0 auto", minWidth: "50px", textAlign: "right", fontSize: "13px", fontWeight: 600, color: isPos ? "#9E1B2E" : "#4A72C8" }}>
          {isPos ? "+" : ""}{value.toFixed(3)}
        </div>
      </div>
    );
  };

  return (
    <div
      role="tabpanel"
      id="ax-tabpanel-why"
      aria-labelledby="ax-tab-why"
      hidden={!active}
      className={cx("ax-shap-section", "ax-tabpanel", !active && "ax-stage-hidden")}
    >
      <div className="ax-shap-header">
        <h2>Why the model responded this way</h2>
        <p className="ax-shap-notice">
          <strong>Important Notice:</strong> These are model-attribution signals, not medical causes or a diagnosis. They show how the uncalibrated explanation model weighted each input toward or away from CAD presence, relative to its baseline (log-odds). They are directional signals: they do not exactly decompose the calibrated probability shown above.
        </p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px" }}>
        <div className="ax-insight-card" style={{ backgroundColor: "#FFFFFF", padding: "20px", borderRadius: "8px", border: "1px solid #EAE2D8" }}>
          <h3 style={{ color: "#9E1B2E", marginBottom: "18px", fontSize: "16px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span aria-hidden="true">↑</span> Factors pushing the model toward CAD present
          </h3>
          {increasing.map(([f, val], i) => renderBar(f, val, true, i))}
          {increasing.length === 0 && <div style={{ color: "var(--ax-text-subtle)", fontSize: "13px" }}>No increasing factors</div>}
        </div>
        <div className="ax-insight-card" style={{ backgroundColor: "#FFFFFF", padding: "20px", borderRadius: "8px", border: "1px solid #EAE2D8" }}>
          <h3 style={{ color: "#4A72C8", marginBottom: "18px", fontSize: "16px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span aria-hidden="true">↓</span> Factors pushing the model toward CAD absent
          </h3>
          {decreasing.map(([f, val], i) => renderBar(f, val, false, i))}
          {decreasing.length === 0 && <div style={{ color: "var(--ax-text-subtle)", fontSize: "13px" }}>No decreasing factors</div>}
        </div>
      </div>
    </div>
  );
}

/* ─── Technical audit: signed log-odds contributions ──────────────────────────────────── */

function AuditPanel({ explanation, active }: { explanation: PredictResponse["explanation"]; active: boolean }) {
  const contributionsArray = (Object.entries(explanation.contributions) as [string, number][]).sort(
    ([, valA], [, valB]) => Math.abs(valB) - Math.abs(valA)
  );
  const maxAbsValue = Math.max(...contributionsArray.map(([, val]) => Math.abs(val)), 1);

  return (
    <div
      role="tabpanel"
      id="ax-tabpanel-audit"
      aria-labelledby="ax-tab-audit"
      hidden={!active}
      className={cx("ax-audit-section", "ax-tabpanel", !active && "ax-stage-hidden")}
    >
      <div className="exp-header">
        <h2>Technical Audit (Logistic Regression)</h2>
        <p>{explanation.note || "Linear feature contributions moving the underlying decision function log-odds."}</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {contributionsArray.map(([feat, val], i) => {
          const pct = Math.min(50, Math.round((Math.abs(val) / maxAbsValue) * 48));
          const isPos = val >= 0;
          return (
            <div key={feat} style={{ display: "flex", alignItems: "center", gap: "14px", fontSize: "13px" }}>
              <div style={{ width: "90px", fontWeight: 600, color: "var(--ax-text-main)" }}>{feat}</div>
              <div style={{ flex: 1, height: "6px", backgroundColor: "#EDE5DC", borderRadius: "3px", overflow: "hidden" }}>
                <div
                  className="ax-bar-fill"
                  style={{ width: `${pct * 2}%`, height: "100%", backgroundColor: isPos ? "#9E1B2E" : "#4A72C8", "--i": i } as CSSProperties}
                />
              </div>
              <div style={{ width: "60px", textAlign: "right", fontFamily: "monospace", fontWeight: 600, color: isPos ? "#9E1B2E" : "#4A72C8" }}>
                {isPos ? "+" : ""}{val.toFixed(4)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
