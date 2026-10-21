"use client";

import React, { useState, useCallback, useMemo } from "react";
import { predict, ApiError } from "../../lib/api";
import { PredictRequest, PredictResponse } from "../../types";
import "./assessment.css";
import CoronaryArteryVisual from "./CoronaryArteryVisual";

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

const CP_LABELS: Record<number, string> = { 0: "Typical Angina", 1: "Atypical Angina", 2: "Non-anginal Pain", 3: "Asymptomatic" };
const SEX_LABELS: Record<number, string> = { 0: "Female", 1: "Male" };
const FBS_LABELS: Record<number, string> = { 0: "False", 1: "True" };
const RESTECG_LABELS: Record<number, string> = { 0: "Normal", 1: "ST-T Wave Abnormality", 2: "LV Hypertrophy" };
const EXANG_LABELS: Record<number, string> = { 0: "No", 1: "Yes" };
const SLOPE_LABELS: Record<number, string> = { 0: "Upsloping", 1: "Flat", 2: "Downsloping" };
const THAL_LABELS: Record<number, string> = { 0: "Unknown", 1: "Normal", 2: "Fixed Defect", 3: "Reversable Defect" };

export default function Page() {
  const [formData, setFormData] = useState<PredictRequest>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [currentStage, setCurrentStage] = useState(0); // Starts cleanly at Step 1 (Patient Profile)
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

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

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
      setTimeout(() => {
        const el = document.getElementById("result-section");
        if (el && typeof el.scrollIntoView === "function") {
          el.scrollIntoView({ behavior: "smooth" });
        }
      }, 100);
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if ((err instanceof Error && err.name === "AbortError") || err === "timeout") {
        if (err === "timeout") {
          setError("Request timed out. Please try again.");
        }
        return;
      }

      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred while communicating with the backend. Please check your connection.");
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, [formData]);

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
      setCurrentStage((s) => s + 1);
    }
  }, [currentStage]);

  const goPrev = useCallback(() => {
    if (currentStage > 0) {
      setCurrentStage((s) => s - 1);
    }
  }, [currentStage]);

  const goToStep = useCallback((idx: number) => {
    setCurrentStage(idx);
  }, []);

  /* ─── Dynamically Derived Progress & Completion Indicators ─── */

  // Summaries per stage based on actual form values
  const railSummaries = useMemo(() => [
    `Age ${formData.age}, ${SEX_LABELS[formData.sex]}`,
    `BP ${formData.trestbps}, Chol ${formData.chol}`,
    `HR ${formData.thalach}, Angina ${EXANG_LABELS[formData.exang]}`,
    `${CP_LABELS[formData.cp]}, Vessels ${formData.ca}`,
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

  /* ─── SHAP Explanation Renderer ─── */
  const renderShapExplanation = (shap: PredictResponse["shap_equivalent_explanation"], probability: number) => {
    if (!shap) return null;
    const contributionsArray = Object.entries(shap.contributions) as [string, number][];
    const increasing = contributionsArray.filter(([, val]) => val > 0).sort((a, b) => b[1] - a[1]);
    const decreasing = contributionsArray.filter(([, val]) => val <= 0).sort((a, b) => a[1] - b[1]);
    const maxAbsValue = Math.max(...contributionsArray.map(([, val]) => Math.abs(val)), 1);

    const renderBar = (feature: string, value: number, isPos: boolean) => {
      const pct = Math.min(100, Math.round((Math.abs(value) / maxAbsValue) * 100));
      return (
        <div key={feature} style={{ display: "flex", alignItems: "center", marginBottom: "12px" }}>
          <div style={{ flex: "0 1 110px", minWidth: "80px", fontWeight: 600, fontSize: "13px", color: "var(--ax-text-main)", textTransform: "capitalize", wordBreak: "break-word", lineHeight: 1.2 }}>
            {feature}
          </div>
          <div role="progressbar" aria-label={`${feature} contribution: ${value.toFixed(3)}`} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} style={{ flex: "1 1 50px", height: "8px", backgroundColor: "#EAE3DC", borderRadius: "4px", overflow: "hidden", margin: "0 16px" }}>
            <div style={{ width: `${pct}%`, height: "100%", backgroundColor: isPos ? "#9E1B2E" : "#4A72C8", borderRadius: "4px" }}></div>
          </div>
          <div style={{ flex: "0 0 auto", minWidth: "50px", textAlign: "right", fontSize: "13px", fontWeight: 600, color: isPos ? "#9E1B2E" : "#4A72C8" }}>
            {isPos ? "+" : ""}{value.toFixed(3)}
          </div>
        </div>
      );
    };

    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px" }}>
        <div style={{ backgroundColor: "#FFFFFF", padding: "20px", borderRadius: "8px", border: "1px solid #EAE2D8" }}>
          <h3 style={{ color: "#9E1B2E", marginBottom: "18px", fontSize: "16px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span aria-hidden="true">↑</span> Factors increasing model output
          </h3>
          {increasing.map(([f, val]) => renderBar(f, val, true))}
          {increasing.length === 0 && <div style={{ color: "var(--ax-text-subtle)", fontSize: "13px" }}>No increasing factors</div>}
        </div>
        <div style={{ backgroundColor: "#FFFFFF", padding: "20px", borderRadius: "8px", border: "1px solid #EAE2D8" }}>
          <h3 style={{ color: "#4A72C8", marginBottom: "18px", fontSize: "16px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span aria-hidden="true">↓</span> Factors decreasing model output
          </h3>
          {decreasing.map(([f, val]) => renderBar(f, val, false))}
          {decreasing.length === 0 && <div style={{ color: "var(--ax-text-subtle)", fontSize: "13px" }}>No decreasing factors</div>}
        </div>
      </div>
    );
  };

  /* ─── Technical Explanation Renderer ─── */
  const renderExplanation = (explanation: PredictResponse["explanation"]) => {
    const contributionsArray = (Object.entries(explanation.contributions) as [string, number][]).sort(
      ([, valA], [, valB]) => Math.abs(valB) - Math.abs(valA)
    );
    const maxAbsValue = Math.max(...contributionsArray.map(([, val]) => Math.abs(val)), 1);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {contributionsArray.map(([feat, val]) => {
          const pct = Math.min(50, Math.round((Math.abs(val) / maxAbsValue) * 48));
          const isPos = val >= 0;
          return (
            <div key={feat} style={{ display: "flex", alignItems: "center", gap: "14px", fontSize: "13px" }}>
              <div style={{ width: "90px", fontWeight: 600, color: "var(--ax-text-main)" }}>{feat}</div>
              <div style={{ flex: 1, height: "6px", backgroundColor: "#EDE5DC", borderRadius: "3px", overflow: "hidden" }}>
                <div style={{ width: `${pct * 2}%`, height: "100%", backgroundColor: isPos ? "#9E1B2E" : "#4A72C8" }}></div>
              </div>
              <div style={{ width: "60px", textAlign: "right", fontFamily: "monospace", fontWeight: 600, color: isPos ? "#9E1B2E" : "#4A72C8" }}>
                {isPos ? "+" : ""}{val.toFixed(4)}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  /* ═══════════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════════════ */

  return (
    <div className="ax-shell">
      {/* ═══════════════════════════════════════════════════════════════════════
          1. LEFT SIDEBAR (Reference Layout + Reference Image 2 Artwork)
          ═══════════════════════════════════════════════════════════════════════ */}
      <aside className="ax-sidebar">
        <div className="ax-sidebar-top">
          {/* CardioVanta Logo */}
          <a href="/" className="ax-sidebar-logo-link" title="CardioVanta Home">
            <img
              src="/brand/cardiovanta-horizontal-transparent.png"
              alt="CardioVanta | Intelligent Cardiovascular Insight"
              className="ax-sidebar-logo"
            />
          </a>

          {/* Navigation Items */}
          <nav className="ax-nav" aria-label="Main Navigation">
            <a href="/" className="ax-nav-item">
              <svg className="ax-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              <span>Overview</span>
            </a>

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
          <a href="/" className="ax-topbar-back">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Back to Overview</span>
          </a>

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
                <div className="ax-intro-eyebrow">
                  <span className="ax-eyebrow-line">—</span> CLINICAL RESEARCH INSTRUMENT
                </div>
                <h1 className="ax-intro-title">Cardiovascular Assessment</h1>
                <p className="ax-intro-sub">
                  Enter the available measurements to generate a modelled probability estimate from the trained diagnostic model.
                </p>
              </div>

              {/* Mountain/Contour Graphic with Slogan */}
              <div className="ax-intro-right">
                <div className="ax-contour-art" aria-hidden="true">
                  <svg viewBox="0 0 120 60" fill="none" stroke="currentColor" className="ax-contour-svg">
                    <path d="M 5 55 Q 35 30 65 48 T 115 40" strokeWidth="1" stroke="#D2C3B5" strokeDasharray="2 2" />
                    <path d="M 0 45 Q 30 20 60 38 T 110 25 T 120 32" strokeWidth="1.2" stroke="#B8A799" />
                    <path d="M 12 32 Q 45 8 78 26 T 120 18" strokeWidth="1.4" stroke="#9E1B2E" strokeOpacity="0.4" />
                    <path d="M 25 20 Q 55 4 85 16 T 120 10" strokeWidth="1" stroke="#A89789" strokeDasharray="3 3" />
                  </svg>
                </div>
                <div className="ax-intro-slogan">
                  <span>SAME DATA.</span>
                  <span>DEEPER INSIGHTS</span>
                  <span>FOR A HEALTHIER</span>
                  <span>TOMORROW.</span>
                </div>
              </div>
            </div>

            {/* Four-Stage Stepper Navigation */}
            <nav className="ax-stepper" role="navigation" aria-label="Assessment steps">
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
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
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
                    {idx < STAGES.length - 1 && <div className="ax-step-line" aria-hidden="true" />}
                  </React.Fragment>
                );
              })}
            </nav>

            {/* Primary Assessment Form Panel Card */}
            <form onSubmit={handleSubmit} className="ax-form-card">
              {/* Card Header */}
              <div className="ax-card-header">
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

              {/* Error banner */}
              {error && (
                <div className="ax-error" role="alert">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <div className="ax-error-text">{error}</div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════
                  STAGE 01: PATIENT PROFILE (rendered in DOM for all tests)
                  ═══════════════════════════════════════════════════════════ */}
              <div className={currentStage === 0 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"}>
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
                      <option value={1}>Male</option>
                      <option value={0}>Female</option>
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
              <div className={currentStage === 1 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"}>
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
                      <option value={0}>False</option>
                      <option value={1}>True</option>
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
                      <option value={0}>Normal</option>
                      <option value={1}>ST-T Wave Abnormality</option>
                      <option value={2}>Left Ventricular Hypertrophy</option>
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
              <div className={currentStage === 2 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"}>
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
                      <option value={0}>No</option>
                      <option value={1}>Yes</option>
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
                      <option value={0}>Upsloping</option>
                      <option value={1}>Flat</option>
                      <option value={2}>Downsloping</option>
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">ST segment slope morphology at peak physical workload</div>
                </div>
              </div>

              {/* ═══════════════════════════════════════════════════════════
                  STAGE 04: DIAGNOSTIC MARKERS (rendered in DOM for all tests)
                  ═══════════════════════════════════════════════════════════ */}
              <div className={currentStage === 3 ? "ax-fields-grid" : "ax-fields-grid ax-stage-hidden"}>
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
                      <option value={0}>Typical Angina</option>
                      <option value={1}>Atypical Angina</option>
                      <option value={2}>Non-anginal Pain</option>
                      <option value={3}>Asymptomatic</option>
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
                      <option value={0}>0</option>
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                      <option value={3}>3</option>
                      <option value={4}>4</option>
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Major coronary vessels (0–4) colored by fluoroscopy</div>
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
                      <option value={0}>Unknown</option>
                      <option value={1}>Normal</option>
                      <option value={2}>Fixed Defect</option>
                      <option value={3}>Reversable Defect</option>
                    </select>
                    <svg className="ax-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="ax-field-helper">Thallium scintigraphy myocardial perfusion evaluation</div>
                </div>
              </div>

              {/* ─── Card Actions (Previous / Continue / Submit) ─── */}
              <div className="ax-card-actions">
                <button
                  type="button"
                  className="ax-btn-prev"
                  onClick={goPrev}
                  disabled={currentStage === 0}
                  style={currentStage === 0 ? { visibility: "hidden" } : undefined}
                >
                  ← Previous
                </button>

                {currentStage < STAGES.length - 1 && (
                  <button type="button" className="ax-btn-continue" onClick={goNext}>
                    Continue →
                  </button>
                )}

                {/* Final Submission Buttons (always in DOM, styled/hidden for tests) */}
                <div className={currentStage === STAGES.length - 1 ? "ax-final-btn-group" : "ax-final-btn-group ax-final-hidden"}>
                  <button type="button" className="ax-btn-reset" onClick={handleReset}>
                    Reset
                  </button>
                  <button type="submit" className="ax-btn-submit" disabled={loading}>
                    {loading ? "Analyzing Profile…" : "Generate Analysis"}
                  </button>
                </div>
              </div>
            </form>

            {/* Scientific Coronary Artery Longitudinal Cutaway Visual */}
            <CoronaryArteryVisual />

            {/* ═══════════════════════════════════════════════════════════
                RESULTS SECTION (Displayed when predictions exist)
                ═══════════════════════════════════════════════════════════ */}
            {result && !loading && (
              <section id="result-section" className="ax-result-section">
                <div className="ax-result-container">
                  <div className="ax-result-prob-block">
                    <div className="ax-result-prob-val">
                      {result.prediction?.probability != null ? (result.prediction.probability * 100).toFixed(1) : "--"}
                      <span>%</span>
                    </div>
                    <div className="ax-result-label">Model Probability</div>
                  </div>
                  <div>
                    <div className="ax-result-info">
                      Based on the provided cardiovascular profile, CardioVanta generated a{" "}
                      <strong>{result.prediction?.probability != null ? (result.prediction.probability * 100).toFixed(1) : "--"}%</strong> modelled probability estimate from the production inference pipeline.
                    </div>
                    <div className="ax-result-threshold">
                      {result.prediction?.threshold_status ? (
                        <strong>{result.prediction.threshold_status}</strong>
                      ) : (
                        "No validated production decision threshold is configured."
                      )}
                    </div>
                    {result.development_range_warning?.outside_development_range && (
                      <div className="ax-warning">
                        <strong>Development Range Guardrail:</strong> Features outside observed development-data range:{" "}
                        {(result.development_range_warning.features || []).join(", ")}.
                      </div>
                    )}
                  </div>
                </div>
              </section>
            )}

            {result && !loading && result.shap_equivalent_explanation && (
              <section className="ax-shap-section">
                <div className="ax-shap-header">
                  <h2>Why the model responded this way</h2>
                  <p className="ax-shap-notice">
                    <strong>Important Notice:</strong> These are model-attribution signals, not medical causes or a diagnosis. They reflect how the mathematical model weighted each input relative to its baseline.
                  </p>
                </div>
                {renderShapExplanation(result.shap_equivalent_explanation, result.prediction.probability)}
              </section>
            )}

            {result && !loading && result.explanation && (
              <section className="ax-audit-section">
                <div className="exp-header">
                  <h2>Technical Audit (Logistic Regression)</h2>
                  <p>{result.explanation.note || "Linear feature contributions moving the underlying decision function log-odds."}</p>
                </div>
                {renderExplanation(result.explanation)}
              </section>
            )}
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
                  <span className="ax-recorded-big">{recordedInputsCount} / 13</span>
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
                          <svg className="ax-rail-status-icon" viewBox="0 0 24 24" fill="#1A1A1A" stroke="#1A1A1A">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="16 9 10 15 8 13" fill="none" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        ) : isActive ? (
                          <svg className="ax-rail-status-icon" viewBox="0 0 24 24" fill="none" stroke="var(--ax-burgundy)" strokeWidth="2.5">
                            <circle cx="12" cy="12" r="10" />
                            <circle cx="12" cy="12" r="4" fill="var(--ax-burgundy)" />
                          </svg>
                        ) : (
                          <svg className="ax-rail-status-icon" viewBox="0 0 24 24" fill="none" stroke="#C8BFB5" strokeWidth="2">
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
                  <span className="ax-input-item-val">{formData.age} yrs</span>
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
                  <span className="ax-input-item-val">{SEX_LABELS[formData.sex]}</span>
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
                      <span className="ax-input-item-val">{formData.trestbps} mmHg</span>
                    </div>

                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
                        </svg>
                        <span>Chol</span>
                      </div>
                      <span className="ax-input-item-val">{formData.chol} mg/dl</span>
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
                      <span className="ax-input-item-val">{formData.thalach} bpm</span>
                    </div>

                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        <span>Angina</span>
                      </div>
                      <span className="ax-input-item-val">{EXANG_LABELS[formData.exang]}</span>
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
                      <span className="ax-input-item-val">{CP_LABELS[formData.cp]}</span>
                    </div>

                    <div className="ax-input-item">
                      <div className="ax-input-item-left">
                        <svg className="ax-input-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="18" cy="6" r="3" />
                        </svg>
                        <span>Vessels</span>
                      </div>
                      <span className="ax-input-item-val">{formData.ca}</span>
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
  );
}
