"use client";

import React, { useState, useCallback, useLayoutEffect, useMemo, useRef, type CSSProperties, type KeyboardEvent } from "react";
import Link from "next/link";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { predict, ApiError } from "../../lib/api";
import { PredictRequest, PredictResponse } from "../../types";
import { CATEGORICAL_LABELS, CATEGORICAL_OPTIONS, type CategoricalFeatureId } from "../../types/generated-features";
import "./assessment.css";
import NextStepStrip from "./NextStepStrip";
import PredictionsUnavailable from "./PredictionsUnavailable";
import { PREDICTION_AVAILABILITY, UNAVAILABLE_CODE } from "../../lib/predictionAvailability";
import { MotionProvider } from "../../components/motion/MotionProvider";
import { AnimatedNumber } from "../../components/motion/AnimatedNumber";
import { RouteTransition } from "../../components/motion/RouteTransition";
import { NAV_BACK, TRANSITION, collapse, formatProbability, panelSwap, revealGroup, revealItem } from "../../lib/motion";

/* ═══════════════════════════════════════════════════════════════════════════
   INITIAL DATA — 13 model features, exact existing defaults & encodings
   ═══════════════════════════════════════════════════════════════════════════ */

export const initialData: PredictRequest = {
  age: 45,
  sex: 1,
  cp: 0,
  trestbps: 120,
  chol: 200,
  fbs: 0,
  restecg: 1,
  thalach: 150,
  exang: 0,
  oldpeak: 1.0,
  slope: 1,
  ca: 0,
  thal: 2,
};

/* ═══════════════════════════════════════════════════════════════════════════
   STAGE CONFIGURATIONS
   ═══════════════════════════════════════════════════════════════════════════ */

interface StageConfig {
  id: string;
  num: string;
  title: string;
  desc: string;
  fieldCount: number;
  badgeDesc: string;
  fieldKeys: (keyof PredictRequest)[];
}

const STAGES: StageConfig[] = [
  {
    id: "profile",
    num: "01",
    title: "Patient Profile",
    desc: "Demographic baseline factors used for model-estimated probability.",
    fieldCount: 2,
    badgeDesc: "Demographic baseline factors recorded at patient intake.",
    fieldKeys: ["age", "sex"],
  },
  {
    id: "vitals",
    num: "02",
    title: "Vitals & Laboratory",
    desc: "Resting hemodynamic and metabolic markers recorded prior to stress testing.",
    fieldCount: 4,
    badgeDesc: "Blood pressure, cholesterol, fasting glucose and resting ECG findings at baseline.",
    fieldKeys: ["trestbps", "chol", "fbs", "restecg"],
  },
  {
    id: "exercise",
    num: "03",
    title: "Exercise Response",
    desc: "Functional chronotropic response and electrophysiologic signs of exertion ischemia.",
    fieldCount: 4,
    badgeDesc: "Peak workload heart rate, angina onset, ST depression and exercise ST slope.",
    fieldKeys: ["thalach", "exang", "oldpeak", "slope"],
  },
  {
    id: "diagnostic",
    num: "04",
    title: "Diagnostic Markers",
    desc: "Symptomatic classification, fluoroscopic vascular assessment, and nuclear perfusion.",
    fieldCount: 3,
    badgeDesc: "Angina symptomatology, fluoroscopic major vessels and nuclear stress thallium.",
    fieldKeys: ["cp", "ca", "thal"],
  },
];

/* ═══════════════════════════════════════════════════════════════════════════
   HUMAN-READABLE ENCODING LABELS
   ═══════════════════════════════════════════════════════════════════════════ */

// Categorical options and labels come from the generated contract
// (contracts/feature_schema.v2.json -> src/types/generated-features.ts). Do not hand-copy them.
// The contract records each code's verification status: cp is patient-matched (Phase 17);
// sex/fbs/restecg/exang/ca 0-3 follow the UCI codebook and project contract; slope and thal
// labels are legacy and unverified; ca=4 and thal=0 are undefined in the UCI codebook.
const CP_LABELS = CATEGORICAL_LABELS.cp;
const SEX_LABELS = CATEGORICAL_LABELS.sex;
const EXANG_LABELS = CATEGORICAL_LABELS.exang;
const CA_LABELS = CATEGORICAL_LABELS.ca;

function renderOptions(feature: CategoricalFeatureId) {
  return CATEGORICAL_OPTIONS[feature].map((o) => (
    <option key={o.code} value={o.code}>{o.display_label}</option>
  ));
}

/** Links back to the landing page are "back" navigations (see RouteTransition). */
const BACK = [NAV_BACK];

/** Fills the slider track up to the current value (CSS reads --pct). Purely visual. */
function sliderFill(value: number, min: number, max: number): React.CSSProperties {
  const pct = Number.isFinite(value) ? Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100)) : 0;
  return { "--pct": `${pct}%` } as React.CSSProperties;
}

/**
 * An error shown in the form card. "unavailable" is the API's structured containment response
 * (predictions switched off server-side): retrying cannot help, so no retry is offered.
 */
interface FormError {
  message: string;
  kind: "unavailable" | "retryable";
}

/* ═══════════════════════════════════════════════════════════════════════════
   RESULTS PANEL (the analysis view that replaces the form card)
   Kept in this file on purpose: backend/tests/test_r0_outcome_semantics.py checks the
   disease-positive outcome and threshold wording in this page source.
   ═══════════════════════════════════════════════════════════════════════════ */

type ResultTab = "summary" | "why" | "audit";

/** Seconds after the panel arrives before the gauge and count-up start. */
const COUNT_DELAY = 0.25;

/** Per-frame formatter for the count-up; module-level so its identity never changes. */
const formatPercentFrame = (n: number) => n.toFixed(1);

const cx = (...names: (string | false | undefined)[]) => names.filter(Boolean).join(" ");

// Human-readable threshold status. The API's class is disease-positive:
// class 1 = P(CAD present) >= threshold, class 0 = below it. Unknown statuses fall back to the raw text.
function describeThreshold(prediction: PredictResponse["prediction"] | undefined): string {
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
function ResultsPanel({ result, tab, onTabChange, onEdit, onNew }: ResultsPanelProps) {
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

/* Containment (Phase 10): while configs/prediction_service.json disables predictions, the page renders
   only the notice. The form, its state and its submit handler are never mounted. */
export default function Page() {
  return (
    <RouteTransition>
      {PREDICTION_AVAILABILITY.enabled ? (
        <AssessmentForm />
      ) : (
        <PredictionsUnavailable notice={PREDICTION_AVAILABILITY.notice} />
      )}
    </RouteTransition>
  );
}

function AssessmentForm() {
  const [formData, setFormData] = useState<PredictRequest>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<FormError | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [currentStage, setCurrentStage] = useState(0); // Starts cleanly at Step 1 (Patient Profile)
  // One-screen layout: results replace the form card instead of appearing below it.
  const [showResults, setShowResults] = useState(false);
  const [resultTab, setResultTab] = useState<ResultTab>("summary");
  // Direction of the last step change; the next step's fields slide in from that side.
  const [direction, setDirection] = useState<1 | -1>(1);
  // The first-paint entrance is CSS (it runs before hydration); once the card has swapped with the
  // results panel, framer-motion animates every later swap, so the CSS entrance must not replay.
  const [hasSwapped, setHasSwapped] = useState(false);
  const abortControllerRef = React.useRef<AbortController | null>(null);

  /* ─── Handlers ─── */

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let parsedValue: number;
    if (type === "number" || type === "range") {
      parsedValue = parseFloat(value);
    } else {
      parsedValue = parseInt(value, 10);
    }
    setFormData((prev: PredictRequest) => ({ ...prev, [name]: parsedValue } as PredictRequest));
  }, []);

  // Sends the current inputs. Shared by the form's submit and the error banner's "Try again".
  const runPrediction = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);

    const timeoutId = setTimeout(() => controller.abort("timeout"), 15000);

    try {
      const response = await predict(formData, controller.signal);
      clearTimeout(timeoutId);
      setResult(response);
      setResultTab("summary");
      setShowResults(true);
      setHasSwapped(true);
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if ((err instanceof Error && err.name === "AbortError") || err === "timeout") {
        if (err === "timeout") {
          setError({ message: "Request timed out. Please try again.", kind: "retryable" });
        }
        return;
      }

      if (err instanceof ApiError) {
        setError({ message: err.message, kind: err.code === UNAVAILABLE_CODE ? "unavailable" : "retryable" });
      } else {
        setError({
          message: "An unexpected error occurred while communicating with the backend. Please check your connection.",
          kind: "retryable",
        });
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, [formData]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    void runPrediction();
  }, [runPrediction]);

  const handleReset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setFormData(initialData);
    setResult(null);
    setError(null);
    setLoading(false);
    setCurrentStage(0);
    setShowResults(false);
    if (typeof window !== "undefined" && typeof window.scrollTo === "function") {
      try {
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch {
        // no-op in headless/jsdom
      }
    }
  }, []);

  const goNext = useCallback(() => {
    if (currentStage < STAGES.length - 1) {
      setDirection(1);
      setCurrentStage((s) => s + 1);
    }
  }, [currentStage]);

  const goPrev = useCallback(() => {
    if (currentStage > 0) {
      setDirection(-1);
      setCurrentStage((s) => s - 1);
    }
  }, [currentStage]);

  const goToStep = useCallback((idx: number) => {
    setDirection(idx >= currentStage ? 1 : -1);
    setCurrentStage(idx);
    setShowResults(false);
  }, [currentStage]);

  // The browser checks `required` and min/max before submitting. If the first invalid field sits on
  // another step, open that step so the browser's message appears next to a visible field instead of
  // a hidden one. Only the first `invalid` event of a submit attempt counts. A ref callback (with
  // React 19 cleanup) attaches the listener whenever the form mounts, including after the results
  // panel's exit animation.
  const attachInvalidListener = useCallback((form: HTMLFormElement | null) => {
    if (!form) return;
    let handled = false;
    const onInvalid = (e: Event) => {
      if (handled) return;
      handled = true;
      queueMicrotask(() => {
        handled = false;
      });
      const field = e.target as HTMLInputElement | HTMLSelectElement | null;
      const idx = STAGES.findIndex((s) => s.fieldKeys.includes(field?.name as keyof PredictRequest));
      if (idx >= 0) {
        // Hidden steps are inert (out of the tab order). Lift that now, synchronously, so the browser
        // can still focus this field and show its message; the re-render below keeps it lifted.
        field?.closest("[inert]")?.removeAttribute("inert");
        setDirection(-1);
        setCurrentStage(idx);
      }
    };
    form.addEventListener("invalid", onInvalid, true);
    return () => form.removeEventListener("invalid", onInvalid, true);
  }, []);

  /* ─── Dynamically Derived Progress & Completion Indicators ─── */

  // Summaries per stage based on actual form values
  const railSummaries = useMemo(() => [
    `Age ${formData.age}, ${SEX_LABELS[formData.sex]}`,
    `BP ${formData.trestbps}, Chol ${formData.chol}`,
    `HR ${formData.thalach}, Angina ${EXANG_LABELS[formData.exang]}`,
    `${CP_LABELS[formData.cp]}, Vessels ${CA_LABELS[formData.ca]}`,
  ], [formData]);

  // Overall recorded inputs count based on stages reached
  const recordedInputsCount = useMemo(() => {
    let count = 0;
    for (let i = 0; i <= currentStage; i++) {
      count += STAGES[i].fieldCount;
    }
    return count;
  }, [currentStage]);

  const stage = STAGES[currentStage];

  // Circle progress math for right rail donut: workflow position (e.g. 1/4, 2/4, 3/4, 4/4)
  const donutRadius = 26;
  const donutCircumference = 2 * Math.PI * donutRadius;
  const progressRatio = (currentStage + 1) / STAGES.length;
  const donutDashoffset = donutCircumference * (1 - progressRatio);

  /* ═══════════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════════════ */

  return (
    <MotionProvider>
    <div className="ax-shell">
      {/* ═══════════════════════════════════════════════════════════════════════
          1. LEFT SIDEBAR (Reference Layout + Reference Image 2 Artwork)
          ═══════════════════════════════════════════════════════════════════════ */}
      <aside className="ax-sidebar">
        <div className="ax-sidebar-top">
          {/* CardioVanta Logo */}
          <Link href="/" transitionTypes={BACK} className="ax-sidebar-logo-link" title="CardioVanta Home">
            <img
              src="/brand/cardiovanta-horizontal-transparent.png"
              alt="CardioVanta | Intelligent Cardiovascular Insight"
              className="ax-sidebar-logo"
            />
          </Link>

          {/* Navigation Items */}
          <nav className="ax-nav" aria-label="Main Navigation">
            <Link href="/" transitionTypes={BACK} className="ax-nav-item">
              <svg className="ax-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              <span>Overview</span>
            </Link>

            <div className="ax-nav-item ax-nav-active">
              <svg className="ax-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                <polyline points="3.5 12 8.5 12 10.5 8 13.5 16 15.5 12 20.5 12" />
              </svg>
              <span>Heart Analysis</span>
            </div>

            <div className="ax-nav-item">
              <svg className="ax-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
              <span>Research</span>
            </div>

            <div className="ax-nav-item">
              <svg className="ax-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>About</span>
            </div>
          </nav>
        </div>

        {/* Oversized Anatomical Heart Engraving Artwork (Reference Image 2) */}
        <div className="ax-sidebar-heart-wrap" aria-hidden="true">
          <img
            src="/images/anatomical-heart.jpg"
            alt=""
            className="ax-sidebar-heart-img"
          />
        </div>
      </aside>

      {/* ═══════════════════════════════════════════════════════════════════════
          2. MAIN COLUMN (Center Area + Right Summary Rail)
          ═══════════════════════════════════════════════════════════════════════ */}
      <main className="ax-main-col">
        {/* Top Navigation Bar */}
        <header className="ax-topbar">
          <Link href="/" transitionTypes={BACK} className="ax-topbar-back">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Back to Overview</span>
          </Link>

          <div className="ax-topbar-center">
            ASSESSMENT WORKFLOW
          </div>

          <div className="ax-topbar-right">
            <div className="ax-topbar-datetime">
              <span className="ax-topbar-date">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                Oct 26, 2024
              </span>
              <span className="ax-topbar-time">10:24 AM</span>
            </div>
            <div className="ax-topbar-avatar" title="Investigator Profile">
              PV
            </div>
          </div>
        </header>

        {/* Content Body Grid */}
        <div className="ax-body-grid">
          {/* ─── Center Primary Form Area ─── */}
          <div className="ax-center-area">
            {/* Page Introduction */}
            <div className="ax-intro">
              <div className="ax-intro-left">
                <div className="ax-intro-eyebrow cv-rise" style={{ "--cv-i": 0 } as React.CSSProperties}>
                  <span className="ax-eyebrow-line">—</span> CLINICAL RESEARCH INSTRUMENT
                </div>
                <h1 className="ax-intro-title cv-rise" style={{ "--cv-i": 1 } as React.CSSProperties}>Cardiovascular Assessment</h1>
                <p className="ax-intro-sub cv-rise" style={{ "--cv-i": 2 } as React.CSSProperties}>
                  Enter the available measurements to generate a modelled probability estimate from the trained diagnostic model.
                </p>
              </div>
            </div>

            {/* Four-Stage Stepper Navigation */}
            <nav className="ax-stepper cv-rise" role="navigation" aria-label="Assessment steps" style={{ "--cv-i": 3 } as React.CSSProperties}>
              {STAGES.map((s, idx) => {
                const state = idx === currentStage ? "active" : idx < currentStage ? "completed" : "upcoming";
                return (
                  <React.Fragment key={s.id}>
                    <button
                      type="button"
                      className="ax-step-btn"
                      data-state={state}
                      onClick={() => goToStep(idx)}
                      aria-current={idx === currentStage ? "step" : undefined}
                      aria-label={`${s.num} ${s.title}`}
                    >
                      <span className="ax-step-circle">
                        {idx < currentStage ? (
                          <svg className="ax-step-check" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        ) : (
                          s.num
                        )}
                      </span>
                      <div className="ax-step-info">
                        <span className="ax-step-name">{s.title}</span>
                        <span className="ax-step-sub">
                          {idx < currentStage
                            ? `${s.fieldCount} / ${s.fieldCount} completed`
                            : `0 / ${s.fieldCount} completed`}
                        </span>
                      </div>
                    </button>
                    {idx < STAGES.length - 1 && (
                      <div className="ax-step-line" data-done={idx < currentStage ? "true" : undefined} aria-hidden="true" />
                    )}
                  </React.Fragment>
                );
              })}
            </nav>

            {/* Primary Assessment Form Panel Card ⇄ Results Panel (one at a time; the leaving
                panel finishes its exit before the arriving one enters) */}
            <AnimatePresence mode="wait" initial={false}>
            {showResults && result ? (
              <ResultsPanel
                key="results"
                result={result}
                tab={resultTab}
                onTabChange={setResultTab}
                onEdit={() => setShowResults(false)}
                onNew={handleReset}
              />
            ) : (
            <m.form
              key="form"
              ref={attachInvalidListener}
              onSubmit={handleSubmit}
              className={hasSwapped ? "ax-form-card" : "ax-form-card cv-rise"}
              style={{ "--cv-i": 4 } as React.CSSProperties}
              data-dir={direction > 0 ? "forward" : "back"}
              aria-busy={loading}
              variants={panelSwap}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {/* Card Header (re-keyed per step so its entrance replays on every step change) */}
              <div className="ax-card-header ax-swap-in" key={stage.id}>
                <div className="ax-card-header-left">
                  <div className="ax-card-step-eyebrow">STEP {stage.num} OF 04</div>
                  <h2 className="ax-card-title">{stage.title}</h2>
                  <p className="ax-card-desc">{stage.desc}</p>
                </div>

                <div className="ax-card-badge">
                  <svg className="ax-badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 2v7.31L4.67 19.1A2 2 0 0 0 6.42 22h11.16a2 2 0 0 0 1.75-2.9L14 9.31V2" />
                    <path d="M8.5 2h7" />
                    <path d="M7 16h10" />
                  </svg>
                  <div className="ax-badge-text-wrap">
                    <div className="ax-badge-count">{stage.fieldCount} FIELDS</div>
                    <div className="ax-badge-desc">{stage.badgeDesc}</div>
                  </div>
                </div>
              </div>

              {/* Scrollable body: only this region scrolls when the window is too short */}
              <div className="ax-card-body">
              {/* Error banner: expands into place and stays until the next attempt or reset. */}
              <AnimatePresence initial={false}>
                {error && (
                  <m.div key="error" className="ax-error-wrap" variants={collapse} initial="initial" animate="animate" exit="exit">
                    <div className={error.kind === "unavailable" ? "ax-error ax-error--paused" : "ax-error"} role="alert">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      <div className="ax-error-text">{error.message}</div>
                      {error.kind === "retryable" && (
                        <button type="button" className="ax-error-retry" onClick={() => void runPrediction()} disabled={loading}>
                          Try again
                        </button>
                      )}
                    </div>
                  </m.div>
                )}
              </AnimatePresence>

              {/* ═══════════════════════════════════════════════════════════
                  STAGE 01: PATIENT PROFILE (rendered in DOM for all tests)
                  ═══════════════════════════════════════════════════════════ */}
              <div className={currentStage === 0 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"} inert={currentStage !== 0}>
                {/* Age */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                      <label className="ax-field-label" htmlFor="age">Age</label>
                    </div>
                    <span className="ax-field-code">age</span>
                  </div>
                  <div className="ax-input-row">
                    <input
                      className="ax-input-control"
                      type="number"
                      id="age"
                      name="age"
                      value={formData.age}
                      onChange={handleChange}
                      required
                      min="1"
                      max="110"
                    />
                    <span className="ax-unit-badge">yrs</span>
                  </div>
                  <div className="ax-field-helper">Adult cohort range: 29–77 yrs · Development median: 55</div>
                  <div className="ax-slider-container">
                    <div className="ax-slider-track-wrap">
                      <input
                        type="range"
                        className="ax-slider-range"
                        name="age"
                        min="20"
                        max="90"
                        value={formData.age}
                        style={sliderFill(formData.age, 20, 90)}
                        onChange={handleChange}
                        aria-hidden="true"
                        tabIndex={-1}
                      />
                    </div>
                    <div className="ax-slider-labels">
                      <span>20</span>
                      <span className="ax-slider-curr-val">{formData.age}</span>
                      <span>90</span>
                    </div>
                  </div>
                </div>

                {/* Sex */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="4" />
                        <path d="M12 2v2" />
                        <path d="M12 20v2" />
                        <path d="M2 12h2" />
                        <path d="M20 12h2" />
                      </svg>
                      <label className="ax-field-label" htmlFor="sex">Sex</label>
                    </div>
                    <span className="ax-field-code">sex</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="sex" name="sex" value={formData.sex} onChange={handleChange}>
                      <option value={1}>{SEX_LABELS[1]}</option>
                      <option value={0}>{SEX_LABELS[0]}</option>
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Biological sex recorded at baseline intake</div>
                </div>
              </div>

              {/* ═══════════════════════════════════════════════════════════
                  STAGE 02: VITALS & LABORATORY (Exact Reference Image 1 Match)
                  ═══════════════════════════════════════════════════════════ */}
              <div className={currentStage === 1 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"} inert={currentStage !== 1}>
                {/* Resting Blood Pressure */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                        <path d="M3 12h4l2-3 3 6 2-3h7" />
                      </svg>
                      <label className="ax-field-label" htmlFor="trestbps">Resting Blood Pressure</label>
                    </div>
                    <span className="ax-field-code">trestbps</span>
                  </div>
                  <div className="ax-input-row">
                    <input
                      className="ax-input-control"
                      type="number"
                      id="trestbps"
                      name="trestbps"
                      value={formData.trestbps}
                      onChange={handleChange}
                      required
                    />
                    <span className="ax-unit-badge">mmHg</span>
                  </div>
                  <div className="ax-field-helper">Resting systolic pressure on admission (standard: 90–140 mmHg)</div>
                  <div className="ax-slider-container">
                    <div className="ax-slider-track-wrap">
                      <input
                        type="range"
                        className="ax-slider-range"
                        name="trestbps"
                        min="90"
                        max="140"
                        value={Math.min(140, Math.max(90, formData.trestbps))}
                        style={sliderFill(formData.trestbps, 90, 140)}
                        onChange={handleChange}
                        aria-hidden="true"
                        tabIndex={-1}
                      />
                    </div>
                    <div className="ax-slider-labels">
                      <span>90</span>
                      <span className="ax-slider-curr-val">{formData.trestbps}</span>
                      <span>140</span>
                    </div>
                  </div>
                </div>

                {/* Serum Cholesterol */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
                      </svg>
                      <label className="ax-field-label" htmlFor="chol">
                        <span>Serum Cholesterol (mg/dl)</span>
                        <span className="sr-only">Serum Cholestoral</span>
                      </label>
                    </div>
                    <span className="ax-field-code">chol</span>
                  </div>
                  <div className="ax-input-row">
                    <input
                      className="ax-input-control"
                      type="number"
                      id="chol"
                      name="chol"
                      value={formData.chol}
                      onChange={handleChange}
                      required
                    />
                    <span className="ax-unit-badge">mg/dl</span>
                  </div>
                  <div className="ax-field-helper">Total serum cholesterol · Clinical desirable threshold: &lt; 200 mg/dl</div>
                  <div className="ax-slider-container">
                    <div className="ax-slider-track-wrap">
                      <input
                        type="range"
                        className="ax-slider-range"
                        name="chol"
                        min="100"
                        max="400"
                        value={Math.min(400, Math.max(100, formData.chol))}
                        style={sliderFill(formData.chol, 100, 400)}
                        onChange={handleChange}
                        aria-hidden="true"
                        tabIndex={-1}
                      />
                    </div>
                    <div className="ax-slider-labels">
                      <span>100</span>
                      <span className="ax-slider-curr-val">{formData.chol}</span>
                      <span>400</span>
                    </div>
                  </div>
                </div>

                {/* Fasting Blood Sugar */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M6 3h12v2H6z" />
                        <path d="M8 5v13a4 4 0 0 0 8 0V5" />
                        <line x1="8" y1="11" x2="16" y2="11" />
                      </svg>
                      <label className="ax-field-label" htmlFor="fbs">Fasting Blood Sugar &gt; 120 mg/dl</label>
                    </div>
                    <span className="ax-field-code">fbs</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="fbs" name="fbs" value={formData.fbs} onChange={handleChange}>
                      {renderOptions("fbs")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Fasting blood sugar &gt; 120 mg/dl indicates impaired fasting glycemia</div>
                </div>

                {/* Resting ECG Results */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                      </svg>
                      <label className="ax-field-label" htmlFor="restecg">Resting ECG Results</label>
                    </div>
                    <span className="ax-field-code">restecg</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="restecg" name="restecg" value={formData.restecg} onChange={handleChange}>
                      {renderOptions("restecg")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Baseline 12-lead electrocardiographic findings at rest</div>
                </div>
              </div>

              {/* ═══════════════════════════════════════════════════════════
                  STAGE 03: EXERCISE RESPONSE (rendered in DOM for all tests)
                  ═══════════════════════════════════════════════════════════ */}
              <div className={currentStage === 2 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"} inert={currentStage !== 2}>
                {/* Maximum Heart Rate */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                      </svg>
                      <label className="ax-field-label" htmlFor="thalach">Maximum Heart Rate Achieved</label>
                    </div>
                    <span className="ax-field-code">thalach</span>
                  </div>
                  <div className="ax-input-row">
                    <input
                      className="ax-input-control"
                      type="number"
                      id="thalach"
                      name="thalach"
                      value={formData.thalach}
                      onChange={handleChange}
                      required
                    />
                    <span className="ax-unit-badge">bpm</span>
                  </div>
                  <div className="ax-field-helper">Peak heart rate measured during Bruce exercise protocol</div>
                  <div className="ax-slider-container">
                    <div className="ax-slider-track-wrap">
                      <input
                        type="range"
                        className="ax-slider-range"
                        name="thalach"
                        min="70"
                        max="210"
                        value={formData.thalach}
                        style={sliderFill(formData.thalach, 70, 210)}
                        onChange={handleChange}
                        aria-hidden="true"
                        tabIndex={-1}
                      />
                    </div>
                    <div className="ax-slider-labels">
                      <span>70</span>
                      <span className="ax-slider-curr-val">{formData.thalach}</span>
                      <span>210</span>
                    </div>
                  </div>
                </div>

                {/* Exercise Induced Angina */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      </svg>
                      <label className="ax-field-label" htmlFor="exang">Exercise Induced Angina</label>
                    </div>
                    <span className="ax-field-code">exang</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="exang" name="exang" value={formData.exang} onChange={handleChange}>
                      {renderOptions("exang")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Ischemic chest discomfort provoked by physical exertion</div>
                </div>

                {/* ST Depression */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="2 12 8 12 12 19 16 12 22 12" />
                      </svg>
                      <label className="ax-field-label" htmlFor="oldpeak">ST Depression Induced by Exercise</label>
                    </div>
                    <span className="ax-field-code">oldpeak</span>
                  </div>
                  <div className="ax-input-row">
                    <input
                      className="ax-input-control"
                      type="number"
                      step="0.1"
                      id="oldpeak"
                      name="oldpeak"
                      value={formData.oldpeak}
                      onChange={handleChange}
                      required
                    />
                    <span className="ax-unit-badge">mm</span>
                  </div>
                  <div className="ax-field-helper">ST depression induced by exercise relative to resting baseline</div>
                  <div className="ax-slider-container">
                    <div className="ax-slider-track-wrap">
                      <input
                        type="range"
                        className="ax-slider-range"
                        name="oldpeak"
                        min="0"
                        max="6"
                        step="0.1"
                        value={formData.oldpeak}
                        style={sliderFill(formData.oldpeak, 0, 6)}
                        onChange={handleChange}
                        aria-hidden="true"
                        tabIndex={-1}
                      />
                    </div>
                    <div className="ax-slider-labels">
                      <span>0.0</span>
                      <span className="ax-slider-curr-val">{formData.oldpeak}</span>
                      <span>6.0</span>
                    </div>
                  </div>
                </div>

                {/* Slope of Peak Exercise */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="7" y1="17" x2="17" y2="7" />
                        <polyline points="7 7 17 7 17 17" />
                      </svg>
                      <label className="ax-field-label" htmlFor="slope">Slope of Peak Exercise ST Segment</label>
                    </div>
                    <span className="ax-field-code">slope</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="slope" name="slope" value={formData.slope} onChange={handleChange}>
                      {renderOptions("slope")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">ST segment slope morphology at peak physical workload. Category labels for this field are not yet verified against the training encoding.</div>
                </div>
              </div>

              {/* ═══════════════════════════════════════════════════════════
                  STAGE 04: DIAGNOSTIC MARKERS (rendered in DOM for all tests)
                  ═══════════════════════════════════════════════════════════ */}
              <div className={currentStage === 3 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"} inert={currentStage !== 3}>
                {/* Chest Pain Type */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      <label className="ax-field-label" htmlFor="cp">Chest Pain Type</label>
                    </div>
                    <span className="ax-field-code">cp</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="cp" name="cp" value={formData.cp} onChange={handleChange}>
                      {renderOptions("cp")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Classification of angina symptomatology</div>
                </div>

                {/* Number of Major Vessels */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="6" y1="3" x2="6" y2="15" />
                        <circle cx="18" cy="6" r="3" />
                        <circle cx="6" cy="18" r="3" />
                        <path d="M18 9a9 9 0 0 1-9 9" />
                      </svg>
                      <label className="ax-field-label" htmlFor="ca">Number of Major Vessels</label>
                    </div>
                    <span className="ax-field-code">ca</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="ca" name="ca" value={formData.ca} onChange={handleChange}>
                      {renderOptions("ca")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Major coronary vessels (0–3) colored by fluoroscopy. Code 4 is outside the UCI codebook; its meaning is unverified.</div>
                </div>

                {/* Thallium Stress Test */}
                <div className="ax-field-box">
                  <div className="ax-field-header">
                    <div className="ax-field-label-group">
                      <svg className="ax-field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <circle cx="12" cy="12" r="4" />
                        <line x1="4.93" y1="4.93" x2="9.17" y2="9.17" />
                        <line x1="14.83" y1="14.83" x2="19.07" y2="19.07" />
                        <line x1="14.83" y1="9.17" x2="19.07" y2="4.93" />
                        <line x1="4.93" y1="19.07" x2="9.17" y2="14.83" />
                      </svg>
                      <label className="ax-field-label" htmlFor="thal">Thallium Stress Test</label>
                    </div>
                    <span className="ax-field-code">thal</span>
                  </div>
                  <div className="ax-select-wrap">
                    <select className="ax-select-control" id="thal" name="thal" value={formData.thal} onChange={handleChange}>
                      {renderOptions("thal")}
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Thallium scintigraphy myocardial perfusion evaluation. Category labels for this field are not yet verified against the training encoding.</div>
                </div>
              </div>
              </div>

              {/* ─── Card Actions (Previous / Up-next strip / Continue / Submit) ─── */}
              <div className="ax-card-actions">
                <button
                  type="button"
                  className="ax-btn-prev"
                  onClick={goPrev}
                  disabled={currentStage === 0}
                  style={currentStage === 0 ? { visibility: "hidden" } : undefined}
                >
                  <span className="ax-btn-arrow ax-btn-arrow--back" aria-hidden="true">←</span> Previous
                </button>

                <NextStepStrip
                  key={currentStage}
                  stages={STAGES}
                  currentStage={currentStage}
                  loading={loading}
                  hasResult={result != null && !loading}
                  onViewResult={() => setShowResults(true)}
                />

                {currentStage < STAGES.length - 1 && (
                  <button type="button" className="ax-btn-continue" onClick={goNext}>
                    Continue <span className="ax-btn-arrow" aria-hidden="true">→</span>
                  </button>
                )}

                {/* Final Submission Buttons (always in DOM, styled/hidden for tests) */}
                <div className={currentStage === STAGES.length - 1 ? "ax-final-btn-group" : "ax-final-btn-group ax-final-hidden"} inert={currentStage !== STAGES.length - 1}>
                  <button type="button" className="ax-btn-reset" onClick={handleReset}>
                    Reset
                  </button>
                  <button type="submit" className="ax-btn-submit" disabled={loading} aria-busy={loading}>
                    {loading && <span className="ax-spinner" aria-hidden="true" />}
                    {loading ? "Analyzing Profile…" : "Generate Analysis"}
                  </button>
                </div>
              </div>
            </m.form>
            )}
            </AnimatePresence>
          </div>

          {/* ═════════════════════════════════════════════════════════════
              3. RIGHT-HAND ASSESSMENT SUMMARY RAIL
              ═════════════════════════════════════════════════════════════ */}
          <aside className="ax-summary-rail" aria-label="Assessment Progress & Summary">
            {/* 1. Assessment Progress Widget */}
            <div>
              <div className="ax-rail-section-title">ASSESSMENT PROGRESS</div>
              <div className="ax-progress-widget">
                <div className="ax-donut-wrap">
                  <svg className="ax-donut-svg" viewBox="0 0 64 64">
                    <circle
                      className="ax-donut-bg"
                      cx="32"
                      cy="32"
                      r={donutRadius}
                      fill="none"
                      strokeWidth="5"
                    />
                    <circle
                      className="ax-donut-fg"
                      cx="32"
                      cy="32"
                      r={donutRadius}
                      fill="none"
                      strokeWidth="5"
                      strokeDasharray={donutCircumference}
                      strokeDashoffset={donutDashoffset}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="ax-donut-text">{currentStage + 1} / 4</span>
                </div>
                <div className="ax-progress-counts">
                  <span className="ax-recorded-big" key={recordedInputsCount}>{recordedInputsCount} / 13</span>
                  <span className="ax-recorded-label">inputs recorded</span>
                </div>
              </div>

              {/* Four-stage completion list */}
              <div className="ax-rail-stages">
                {STAGES.map((s, idx) => {
                  const isDone = idx < currentStage;
                  const isActive = idx === currentStage;
                  return (
                    <div className="ax-rail-stage-row" key={s.id}>
                      <div className="ax-rail-stage-left">
                        {isDone ? (
                          <svg key="done" className="ax-rail-status-icon" viewBox="0 0 24 24" fill="#1A1A1A" stroke="#1A1A1A" aria-hidden="true">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="16 9 10 15 8 13" fill="none" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        ) : isActive ? (
                          <svg key="active" className="ax-rail-status-icon" viewBox="0 0 24 24" fill="none" stroke="var(--ax-burgundy)" strokeWidth="2.5" aria-hidden="true">
                            <circle cx="12" cy="12" r="10" />
                            <circle cx="12" cy="12" r="4" fill="var(--ax-burgundy)" />
                          </svg>
                        ) : (
                          <svg key="todo" className="ax-rail-status-icon" viewBox="0 0 24 24" fill="none" stroke="#C8BFB5" strokeWidth="2" aria-hidden="true">
                            <circle cx="12" cy="12" r="10" />
                          </svg>
                        )}
                        <div className="ax-rail-stage-meta">
                          <span className="ax-rail-stage-title">{s.title}</span>
                          <span className="ax-rail-stage-desc">
                            {idx <= currentStage ? railSummaries[idx] : "Awaiting input"}
                          </span>
                        </div>
                      </div>
                      <span className="ax-rail-stage-count">
                        {isDone ? `${s.fieldCount} / ${s.fieldCount}` : `0 / ${s.fieldCount}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="ax-rail-divider" />

            {/* 2. Current Inputs (Only displays inputs from stages reached so far!) */}
            <div>
              <div className="ax-inputs-header">
                <span className="ax-rail-section-title" style={{ marginBottom: 0 }}>CURRENT INPUTS</span>
                <button type="button" className="ax-edit-link" onClick={() => goToStep(0)}>
                  Edit
                </button>
              </div>

              <div className="ax-inputs-list">
                {/* Stage 0 inputs: always visible */}
                <div className="ax-input-item">
                  <div className="ax-input-item-left">
                    <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <span>Age</span>
                  </div>
                  <span className="ax-input-item-val" key={String(formData.age)}>{formData.age} yrs</span>
                </div>

                <div className="ax-input-item">
                  <div className="ax-input-item-left">
                    <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="4" />
                      <path d="M12 2v2" />
                      <path d="M12 20v2" />
                    </svg>
                    <span>Sex</span>
                  </div>
                  <span className="ax-input-item-val" key={String(formData.sex)}>{SEX_LABELS[formData.sex]}</span>
                </div>

                {/* Stage 1 inputs: visible when currentStage >= 1 */}
                {currentStage >= 1 && (
                  <>
                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                        </svg>
                        <span>BP</span>
                      </div>
                      <span className="ax-input-item-val" key={String(formData.trestbps)}>{formData.trestbps} mmHg</span>
                    </div>

                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
                        </svg>
                        <span>Chol</span>
                      </div>
                      <span className="ax-input-item-val" key={String(formData.chol)}>{formData.chol} mg/dl</span>
                    </div>
                  </>
                )}

                {/* Stage 2 inputs: visible when currentStage >= 2 */}
                {currentStage >= 2 && (
                  <>
                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                        <span>Max HR</span>
                      </div>
                      <span className="ax-input-item-val" key={String(formData.thalach)}>{formData.thalach} bpm</span>
                    </div>

                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        <span>Angina</span>
                      </div>
                      <span className="ax-input-item-val" key={String(formData.exang)}>{EXANG_LABELS[formData.exang]}</span>
                    </div>
                  </>
                )}

                {/* Stage 3 inputs: visible when currentStage >= 3 */}
                {currentStage >= 3 && (
                  <>
                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" />
                        </svg>
                        <span>Chest Pain</span>
                      </div>
                      <span className="ax-input-item-val" key={String(formData.cp)}>{CP_LABELS[formData.cp]}</span>
                    </div>

                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="18" cy="6" r="3" />
                        </svg>
                        <span>Vessels</span>
                      </div>
                      <span className="ax-input-item-val" key={String(formData.ca)}>{CA_LABELS[formData.ca]}</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="ax-rail-divider" />

            {/* 3. Model Configuration */}
            <div>
              <div className="ax-rail-section-title">MODEL CONFIGURATION</div>
              <div className="ax-model-config">
                <div className="ax-config-row">
                  <span className="ax-config-label">Model</span>
                  <span className="ax-config-val">Logistic Regression</span>
                </div>
                <div className="ax-config-row">
                  <span className="ax-config-label">Feature Set</span>
                  <span className="ax-config-val">UCI Heart (13)</span>
                </div>
                <div className="ax-config-row">
                  <span className="ax-config-label">Calibration</span>
                  <span className="ax-config-val">Platt Sigmoid (5-fold)</span>
                </div>
              </div>
            </div>

            {/* 4. Medical-use notice */}
            <div className="ax-medical-notice">
              <div className="ax-notice-head">
                <svg className="ax-notice-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
                <span className="ax-notice-tag">USE NOTICE</span>
              </div>
              <p className="ax-notice-quote">
                &ldquo;A modelled probability is a decision aid, not a diagnosis &mdash; always confirm findings with a physician.&rdquo;
              </p>
            </div>
          </aside>
        </div>
      </main>
    </div>
    </MotionProvider>
  );
}
