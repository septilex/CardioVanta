"use client";

import React, { useState } from "react";
import { predict, ApiError } from "../../lib/api";
import { PredictRequest, PredictResponse } from "../../types";

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

export default function Page() {
  const [formData, setFormData] = useState<PredictRequest>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const abortControllerRef = React.useRef<AbortController | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let parsedValue: number;
    if (type === "number") {
      parsedValue = parseFloat(value);
    } else {
      parsedValue = parseInt(value, 10);
    }
    setFormData((prev: PredictRequest) => ({ ...prev, [name]: parsedValue } as PredictRequest));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);

    // Timeout to ensure request fails if backend hangs
    const timeoutId = setTimeout(() => controller.abort("timeout"), 15000);

    try {
      const response = await predict(formData, controller.signal);
      clearTimeout(timeoutId);
      setResult(response);
      // scroll to result
      setTimeout(() => {
        const el = document.getElementById('result-section');
        if (el && typeof el.scrollIntoView === 'function') {
          el.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if ((err instanceof Error && err.name === 'AbortError') || err === 'timeout') {
        if (err === 'timeout') {
          setError("Request timed out. Please try again.");
        }
        return; // aborted requests shouldn't alter state beyond timeout error
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
  };

  const handleReset = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setFormData(initialData);
    setResult(null);
    setError(null);
    setLoading(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const renderExplanation = (explanation: PredictResponse["explanation"]) => {
    const contributionsArray = (Object.entries(explanation.contributions) as [string, number][]).sort(
      ([, valA], [, valB]) => Math.abs(valB) - Math.abs(valA)
    );
    
    const maxAbsValue = Math.max(...contributionsArray.map(([, val]) => Math.abs(val)), 1);
    
    return (
      <div className="chart-block">
        <div className="chart-axis-container">
          <div className="chart-axis-line"></div>
          {contributionsArray.map(([feature, value]) => {
            const pct = Math.min(50, Math.round((Math.abs(value) / maxAbsValue) * 48));
            const isPos = value >= 0;
            return (
              <div className="c-row" key={feature}>
                <div className="c-lbl">{feature}</div>
                <div className="c-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${feature} contribution: ${value.toFixed(4)}`}>
                  <div className={`c-bar ${isPos ? 'pos' : 'neg'}`} style={{ width: `${pct}%` }}></div>
                </div>
                <div className="c-val">{isPos ? '+' : ''}{value.toFixed(4)}</div>
              </div>
            );
          })}
        </div>
        
        <div className="chart-footer">
          <div className="cf-item">
            <div className="lbl">Intercept</div>
            <div className="val">{explanation.intercept.toFixed(4)}</div>
          </div>
          <div className="cf-item">
            <div className="lbl">Model Log-Odds</div>
            <div className="val">{explanation.decision_function_log_odds.toFixed(4)}</div>
          </div>
        </div>
      </div>
    );
  };

  const renderShapExplanation = (shap: PredictResponse["shap_equivalent_explanation"], probability: number) => {
    if (!shap) return null;
    const contributionsArray = Object.entries(shap.contributions) as [string, number][];
    
    const increasing = contributionsArray.filter(([, val]) => val > 0).sort((a, b) => b[1] - a[1]);
    const decreasing = contributionsArray.filter(([, val]) => val <= 0).sort((a, b) => a[1] - b[1]);
    const maxAbsValue = Math.max(...contributionsArray.map(([, val]) => Math.abs(val)), 1);

    const renderBar = (feature: string, value: number, isPos: boolean) => {
      const pct = Math.min(100, Math.round((Math.abs(value) / maxAbsValue) * 100));
      return (
        <div key={feature} style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ flex: '0 1 100px', minWidth: '70px', fontWeight: 600, fontSize: '14px', color: 'var(--cv-text-dark-1)', textTransform: 'capitalize', wordBreak: 'break-word', lineHeight: 1.2 }}>{feature}</div>
          <div role="progressbar" aria-label={`${feature} contribution: ${value.toFixed(3)}`} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} style={{ flex: '1 1 50px', height: '8px', backgroundColor: '#EAE3DC', borderRadius: '4px', overflow: 'hidden', margin: '0 16px' }}>
             <div style={{
               width: `${pct}%`,
               height: '100%',
               backgroundColor: isPos ? '#D5495B' : '#4973D5',
               borderRadius: '4px'
             }}></div>
          </div>
          <div style={{ flex: '0 0 auto', minWidth: '50px', textAlign: 'right', fontSize: '14px', fontWeight: 600, color: isPos ? '#D5495B' : '#4973D5' }}>
            {isPos ? '+' : ''}{value.toFixed(3)}
          </div>
        </div>
      );
    };

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px' }}>
        <div style={{ backgroundColor: '#fff', padding: '24px', borderRadius: '12px', border: '1px solid #EAE3DC', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }}>
          <h3 style={{ color: '#D5495B', marginBottom: '24px', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span aria-hidden="true">↑</span> Factors increasing model output
          </h3>
          {increasing.map(([feature, val]) => renderBar(feature, val, true))}
          {increasing.length === 0 && <div style={{ color: '#8C8279', fontSize: '14px' }}>No increasing factors</div>}
        </div>
        <div style={{ backgroundColor: '#fff', padding: '24px', borderRadius: '12px', border: '1px solid #EAE3DC', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }}>
          <h3 style={{ color: '#4973D5', marginBottom: '24px', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span aria-hidden="true">↓</span> Factors decreasing model output
          </h3>
          {decreasing.map(([feature, val]) => renderBar(feature, val, false))}
          {decreasing.length === 0 && <div style={{ color: '#8C8279', fontSize: '14px' }}>No decreasing factors</div>}
        </div>
        
        <div style={{ gridColumn: '1 / -1', marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '24px', justifyContent: 'space-between', padding: '24px 32px', backgroundColor: '#F8F6F4', borderRadius: '12px', border: '1px solid #EAE3DC' }}>
          <div>
            <div style={{ fontSize: '13px', color: '#8C8279', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Baseline / Reference Output</div>
            <div style={{ fontSize: '20px', fontWeight: 600, color: 'var(--cv-text-dark-1)' }}>{shap.expected_value.toFixed(4)} <span style={{ fontSize: '14px', fontWeight: 400, color: '#8C8279' }}>(Log-odds)</span></div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '13px', color: '#8C8279', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Final Model Probability</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--cv-red)' }}>{(probability * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      <header className="header" style={{ height: 'auto', padding: '16px 0' }}>
        <div className="container header-content" style={{ height: 'auto' }}>
          <div className="logo-wrapper">
            <picture>
              <source media="(max-width: 600px)" srcSet="/brand/cardiovanta-icon-transparent.png" />
              <img src="/brand/cardiovanta-horizontal-transparent.png" alt="CardioVanta" className="brand-logo" />
            </picture>
          </div>
          <nav className="header-nav">
            <a href="/" className="nav-link" style={{ textTransform: 'none', letterSpacing: 'normal' }}>&larr; Back to Overview</a>
          </nav>
        </div>
      </header>

      <main>
        <section className="workspace-section" style={{ paddingTop: '56px' }}>
          <div className="container workspace-grid">
            
            <div className="workspace-form-area">
              <div className="workspace-intro">
                <h1 style={{ fontSize: '42px', marginBottom: '14px', color: 'var(--cv-text)' }}>Cardiovascular Assessment</h1>
                <p style={{ fontSize: '16px', color: 'var(--cv-text-muted)', maxWidth: '640px', lineHeight: 1.6 }}>
                  Enter the available measurements below to generate a modelled probability estimate from the trained diagnostic model.
                </p>
                {/* Stage Stepper / Progress Bar */}
                <div className="assessment-stepper" role="navigation" aria-label="Assessment Sections" style={{ padding: '20px 24px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
                  <a href="#section-01" className="stepper-item active">
                    <span className="stepper-dot"></span>
                    <span>01 Patient Profile</span>
                  </a>
                  <span className="stepper-divider"></span>
                  <a href="#section-02" className="stepper-item active">
                    <span className="stepper-dot"></span>
                    <span>02 Vitals &amp; Lab</span>
                  </a>
                  <span className="stepper-divider"></span>
                  <a href="#section-03" className="stepper-item active">
                    <span className="stepper-dot"></span>
                    <span>03 Exercise Response</span>
                  </a>
                  <span className="stepper-divider"></span>
                  <a href="#section-04" className="stepper-item active">
                    <span className="stepper-dot"></span>
                    <span>04 Diagnostic Markers</span>
                  </a>
                </div>
              </div>

              <form onSubmit={handleSubmit}>
                {/* GROUP 01 */}
                <div id="section-01" className="form-group">
                  <div className="form-group-header" style={{ borderBottom: '1px solid var(--cv-border)', paddingBottom: '24px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div className="form-group-title-wrap" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', backgroundColor: 'var(--cv-surface)', color: 'var(--cv-red)', borderRadius: '50%', fontSize: '11px', fontFamily: 'monospace', fontWeight: 600 }}>01</span>
                        <span className="form-group-title" style={{ margin: 0, fontSize: '20px' }}>Patient Profile</span>
                      </div>
                      <span className="form-group-desc" style={{ paddingLeft: '44px' }}>Demographic baseline factors used for clinical risk stratification.</span>
                    </div>
                    <span className="form-group-badge" style={{ backgroundColor: '#F8F6F4', padding: '6px 12px', borderRadius: '4px', border: '1px solid var(--cv-border)', fontSize: '11px', alignSelf: 'flex-start' }}>
                      <span style={{ color: 'var(--cv-text-muted)', marginRight: '6px' }}>REQUIRED FIELDS</span>
                      <span>2</span>
                    </span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="age">
                        <span>Age</span>
                        <span className="input-code" aria-hidden="true">age</span>
                      </label>
                      <div className="input-field-container">
                        <input className="input-control has-unit" type="number" id="age" name="age" value={formData.age} onChange={handleChange} required min="1" max="110" />
                        <span className="input-unit">yrs</span>
                      </div>
                      <span className="input-hint">Adult cohort range: 29–77 yrs · Development median: 55</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="sex">
                        <span>Sex</span>
                        <span className="input-code" aria-hidden="true">sex</span>
                      </label>
                      <select className="input-control" id="sex" name="sex" value={formData.sex} onChange={handleChange}>
                        <option value={1}>Male</option>
                        <option value={0}>Female</option>
                      </select>
                      <span className="input-hint">Biological sex recorded at baseline clinical intake</span>
                    </div>
                  </div>
                </div>

                {/* GROUP 02 */}
                <div id="section-02" className="form-group">
                  <div className="form-group-header" style={{ borderBottom: '1px solid var(--cv-border)', paddingBottom: '24px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div className="form-group-title-wrap" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', backgroundColor: 'var(--cv-surface)', color: 'var(--cv-red)', borderRadius: '50%', fontSize: '11px', fontFamily: 'monospace', fontWeight: 600 }}>02</span>
                        <span className="form-group-title" style={{ margin: 0, fontSize: '20px' }}>Vitals &amp; Laboratory</span>
                      </div>
                      <span className="form-group-desc" style={{ paddingLeft: '44px' }}>Resting hemodynamic and metabolic markers recorded prior to stress testing.</span>
                    </div>
                    <span className="form-group-badge" style={{ backgroundColor: '#F8F6F4', padding: '6px 12px', borderRadius: '4px', border: '1px solid var(--cv-border)', fontSize: '11px', alignSelf: 'flex-start' }}>
                      <span style={{ color: 'var(--cv-text-muted)', marginRight: '6px' }}>REQUIRED FIELDS</span>
                      <span>4</span>
                    </span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="trestbps">
                        <span>Resting Blood Pressure</span>
                        <span className="input-code" aria-hidden="true">trestbps</span>
                      </label>
                      <div className="input-field-container">
                        <input className="input-control has-unit" type="number" id="trestbps" name="trestbps" value={formData.trestbps} onChange={handleChange} required />
                        <span className="input-unit">mmHg</span>
                      </div>
                      <span className="input-hint">Resting systolic pressure on admission (standard: 90–140 mmHg)</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="chol">
                        <span>Serum Cholestoral (mg/dl)</span>
                        <span className="input-code" aria-hidden="true">chol</span>
                      </label>
                      <div className="input-field-container">
                        <input className="input-control has-unit" type="number" id="chol" name="chol" value={formData.chol} onChange={handleChange} required />
                        <span className="input-unit">mg/dl</span>
                      </div>
                      <span className="input-hint">Total serum cholesterol · Clinical desirable threshold: &lt; 200 mg/dl</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="fbs">
                        <span>Fasting Blood Sugar &gt; 120 mg/dl</span>
                        <span className="input-code" aria-hidden="true">fbs</span>
                      </label>
                      <select className="input-control" id="fbs" name="fbs" value={formData.fbs} onChange={handleChange}>
                        <option value={0}>False</option>
                        <option value={1}>True</option>
                      </select>
                      <span className="input-hint">Fasting blood sugar &gt; 120 mg/dl indicates impaired fasting glycemia</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="restecg">
                        <span>Resting ECG Results</span>
                        <span className="input-code" aria-hidden="true">restecg</span>
                      </label>
                      <select className="input-control" id="restecg" name="restecg" value={formData.restecg} onChange={handleChange}>
                        <option value={0}>Normal</option>
                        <option value={1}>ST-T Wave Abnormality</option>
                        <option value={2}>Left Ventricular Hypertrophy</option>
                      </select>
                      <span className="input-hint">Baseline 12-lead electrocardiographic findings at rest</span>
                    </div>
                  </div>
                </div>

                {/* GROUP 03 */}
                <div id="section-03" className="form-group">
                  <div className="form-group-header" style={{ borderBottom: '1px solid var(--cv-border)', paddingBottom: '24px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div className="form-group-title-wrap" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', backgroundColor: 'var(--cv-surface)', color: 'var(--cv-red)', borderRadius: '50%', fontSize: '11px', fontFamily: 'monospace', fontWeight: 600 }}>03</span>
                        <span className="form-group-title" style={{ margin: 0, fontSize: '20px' }}>Exercise Response</span>
                      </div>
                      <span className="form-group-desc" style={{ paddingLeft: '44px' }}>Functional chronotropic response and electrophysiologic signs of exertion ischemia.</span>
                    </div>
                    <span className="form-group-badge" style={{ backgroundColor: '#F8F6F4', padding: '6px 12px', borderRadius: '4px', border: '1px solid var(--cv-border)', fontSize: '11px', alignSelf: 'flex-start' }}>
                      <span style={{ color: 'var(--cv-text-muted)', marginRight: '6px' }}>REQUIRED FIELDS</span>
                      <span>4</span>
                    </span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="thalach">
                        <span>Maximum Heart Rate Achieved</span>
                        <span className="input-code" aria-hidden="true">thalach</span>
                      </label>
                      <div className="input-field-container">
                        <input className="input-control has-unit" type="number" id="thalach" name="thalach" value={formData.thalach} onChange={handleChange} required />
                        <span className="input-unit">bpm</span>
                      </div>
                      <span className="input-hint">Peak heart rate measured during Bruce exercise protocol</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="exang">
                        <span>Exercise Induced Angina</span>
                        <span className="input-code" aria-hidden="true">exang</span>
                      </label>
                      <select className="input-control" id="exang" name="exang" value={formData.exang} onChange={handleChange}>
                        <option value={0}>No</option>
                        <option value={1}>Yes</option>
                      </select>
                      <span className="input-hint">Ischemic chest discomfort provoked by physical exertion</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="oldpeak">
                        <span>ST Depression Induced by Exercise</span>
                        <span className="input-code" aria-hidden="true">oldpeak</span>
                      </label>
                      <div className="input-field-container">
                        <input className="input-control has-unit" type="number" step="0.1" id="oldpeak" name="oldpeak" value={formData.oldpeak} onChange={handleChange} required />
                        <span className="input-unit">mm</span>
                      </div>
                      <span className="input-hint">ST depression induced by exercise relative to resting baseline</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="slope">
                        <span>Slope of Peak Exercise ST Segment</span>
                        <span className="input-code" aria-hidden="true">slope</span>
                      </label>
                      <select className="input-control" id="slope" name="slope" value={formData.slope} onChange={handleChange}>
                        <option value={0}>Upsloping</option>
                        <option value={1}>Flat</option>
                        <option value={2}>Downsloping</option>
                      </select>
                      <span className="input-hint">ST segment slope morphology at peak physical workload</span>
                    </div>
                  </div>
                </div>

                {/* GROUP 04 */}
                <div id="section-04" className="form-group">
                  <div className="form-group-header" style={{ borderBottom: '1px solid var(--cv-border)', paddingBottom: '24px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div className="form-group-title-wrap" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', backgroundColor: 'var(--cv-surface)', color: 'var(--cv-red)', borderRadius: '50%', fontSize: '11px', fontFamily: 'monospace', fontWeight: 600 }}>04</span>
                        <span className="form-group-title" style={{ margin: 0, fontSize: '20px' }}>Diagnostic Markers</span>
                      </div>
                      <span className="form-group-desc" style={{ paddingLeft: '44px' }}>Symptomatic classification, fluoroscopic vascular assessment, and nuclear perfusion.</span>
                    </div>
                    <span className="form-group-badge" style={{ backgroundColor: '#F8F6F4', padding: '6px 12px', borderRadius: '4px', border: '1px solid var(--cv-border)', fontSize: '11px', alignSelf: 'flex-start' }}>
                      <span style={{ color: 'var(--cv-text-muted)', marginRight: '6px' }}>REQUIRED FIELDS</span>
                      <span>3</span>
                    </span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="cp">
                        <span>Chest Pain Type</span>
                        <span className="input-code" aria-hidden="true">cp</span>
                      </label>
                      <select className="input-control" id="cp" name="cp" value={formData.cp} onChange={handleChange}>
                        <option value={0}>Typical Angina</option>
                        <option value={1}>Atypical Angina</option>
                        <option value={2}>Non-anginal Pain</option>
                        <option value={3}>Asymptomatic</option>
                      </select>
                      <span className="input-hint">Clinical classification of angina symptomatology</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="ca">
                        <span>Number of Major Vessels</span>
                        <span className="input-code" aria-hidden="true">ca</span>
                      </label>
                      <select className="input-control" id="ca" name="ca" value={formData.ca} onChange={handleChange}>
                        <option value={0}>0</option>
                        <option value={1}>1</option>
                        <option value={2}>2</option>
                        <option value={3}>3</option>
                        <option value={4}>4</option>
                      </select>
                      <span className="input-hint">Major coronary vessels (0–3) colored by fluoroscopy</span>
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="thal">
                        <span>Thalassemia</span>
                        <span className="input-code" aria-hidden="true">thal</span>
                      </label>
                      <select className="input-control" id="thal" name="thal" value={formData.thal} onChange={handleChange}>
                        <option value={0}>Unknown</option>
                        <option value={1}>Normal</option>
                        <option value={2}>Fixed Defect</option>
                        <option value={3}>Reversable Defect</option>
                      </select>
                      <span className="input-hint">Thallium scintigraphy myocardial perfusion evaluation</span>
                    </div>
                  </div>
                </div>

                {/* Error Banner */}
                {error && (
                  <div className="clinical-error-banner" role="alert">
                    <svg className="clinical-error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="12" y1="8" x2="12" y2="12"></line>
                      <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <div className="clinical-error-text">{error}</div>
                  </div>
                )}
                
                {/* Bottom Action & Telemetry Bar */}
                <div className="form-action-bar">
                  <div className="form-status-info">
                    <div className="form-status-badge">
                      <span className="form-status-dot"></span>
                      <span>13/13 CLINICAL INPUTS RECORDED</span>
                    </div>
                    <span>MODEL: LOGISTIC REGRESSION (SIGMOID CALIBRATED) · V1.0.0</span>
                  </div>
                  <div className="form-action-buttons">
                    <button type="button" onClick={handleReset} className="btn-secondary" style={{ padding: '16px 32px', fontSize: '15px' }}>
                      Reset
                    </button>
                    <button type="submit" className="submit-btn" disabled={loading} style={{ width: 'auto', padding: '16px 36px', fontSize: '16px' }}>
                      {loading ? "Analyzing Profile..." : "Generate Analysis"}
                    </button>
                  </div>
                </div>
              </form>
            </div>

            {/* Sticky Panel */}
            <div className="workspace-summary-area">
              <div className="sticky-summary">
                <div className="summary-eyebrow">
                  <span>▪</span>
                  <span>MODEL OUTPUT</span>
                </div>
                
                {!result && !loading && (
                  <div>
                    <h2 className="summary-status-title" style={{ fontSize: '28px', marginBottom: '16px' }}>Awaiting Input</h2>
                    <p className="summary-desc-text" style={{ fontSize: '14px', lineHeight: 1.6, marginBottom: '32px' }}>
                      Complete the profile to generate a modelled probability. The estimate draws on all 13 clinical inputs at once — partial profiles are not scored.
                    </p>
                    <div className="summary-matrix" style={{ gap: '0', padding: '0', border: 'none' }}>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <span className="summary-matrix-label" style={{ color: 'var(--cv-text)', fontSize: '13px', fontWeight: 500 }}>Patient Profile</span>
                          <span style={{ fontSize: '11px', color: 'var(--cv-text-muted)', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--cv-font-body), sans-serif' }}>Age {formData.age}, {formData.sex === 1 ? 'Male' : 'Female'}</span>
                        </div>
                        <span className="summary-matrix-status recorded" style={{ fontSize: '11px', backgroundColor: 'var(--cv-surface)', padding: '4px 8px', borderRadius: '4px' }}>recorded</span>
                      </div>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <span className="summary-matrix-label" style={{ color: 'var(--cv-text)', fontSize: '13px', fontWeight: 500 }}>Vitals &amp; Lab</span>
                          <span style={{ fontSize: '11px', color: 'var(--cv-text-muted)', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--cv-font-body), sans-serif' }}>BP: {formData.trestbps}mmHg, Chol: {formData.chol}mg/dl</span>
                        </div>
                        <span className="summary-matrix-status recorded" style={{ fontSize: '11px', backgroundColor: 'var(--cv-surface)', padding: '4px 8px', borderRadius: '4px' }}>recorded</span>
                      </div>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <span className="summary-matrix-label" style={{ color: 'var(--cv-text)', fontSize: '13px', fontWeight: 500 }}>Exercise Response</span>
                          <span style={{ fontSize: '11px', color: 'var(--cv-text-muted)', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--cv-font-body), sans-serif' }}>Max HR: {formData.thalach}, Angina: {formData.exang === 1 ? 'Yes' : 'No'}</span>
                        </div>
                        <span className="summary-matrix-status recorded" style={{ fontSize: '11px', backgroundColor: 'var(--cv-surface)', padding: '4px 8px', borderRadius: '4px' }}>recorded</span>
                      </div>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <span className="summary-matrix-label" style={{ color: 'var(--cv-text)', fontSize: '13px', fontWeight: 500 }}>Diagnostic Markers</span>
                          <span style={{ fontSize: '11px', color: 'var(--cv-text-muted)', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--cv-font-body), sans-serif' }}>CP Type: {formData.cp}, Vessels: {formData.ca}</span>
                        </div>
                        <span className="summary-matrix-status recorded" style={{ fontSize: '11px', backgroundColor: 'var(--cv-surface)', padding: '4px 8px', borderRadius: '4px' }}>recorded</span>
                      </div>
                    </div>
                    <div className="summary-specs" style={{ marginTop: '24px', backgroundColor: 'var(--cv-surface)', padding: '16px', borderRadius: '4px', border: '1px solid var(--cv-border)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', color: 'var(--cv-text)' }}>
                        <span>Target Model</span>
                        <strong>Logistic Regression</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span>Feature Set</span>
                        <span>UCI Heart (13)</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Calibration</span>
                        <span>Platt Sigmoid (5-fold)</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {loading && (
                  <div>
                    <h2 className="summary-status-title" style={{ fontSize: '28px', color: 'var(--cv-red)', marginBottom: '16px' }}>Evaluating Profile...</h2>
                    <p className="summary-desc-text" style={{ fontSize: '14px', lineHeight: 1.6, marginBottom: '32px' }}>
                      Evaluating cardiovascular markers via the prediction API. Validating vector bounds and running inference.
                    </p>
                    <div className="summary-matrix" style={{ gap: '0', padding: '0', border: 'none' }}>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <span className="summary-matrix-label" style={{ fontSize: '13px', color: 'var(--cv-text)' }}>01 Vector validation</span>
                        <span className="summary-matrix-status recorded" style={{ color: 'var(--cv-success)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}><span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--cv-success)' }}></span> complete</span>
                      </div>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <span className="summary-matrix-label" style={{ fontSize: '13px', color: 'var(--cv-text)' }}>02 Feature scaling</span>
                        <span className="summary-matrix-status recorded" style={{ color: 'var(--cv-success)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}><span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--cv-success)' }}></span> complete</span>
                      </div>
                      <div className="summary-matrix-row" style={{ padding: '16px 0', borderBottom: '1px solid var(--cv-border)' }}>
                        <span className="summary-matrix-label" style={{ fontSize: '13px', color: 'var(--cv-text)' }}>03 Calibrated probability</span>
                        <span className="summary-matrix-status pending animate-pulse" style={{ fontSize: '11px' }}>computing...</span>
                      </div>
                    </div>
                  </div>
                )}

                {result && !loading && (
                  <div>
                    <h2 className="summary-status-title" style={{ fontSize: '28px', marginBottom: '24px' }}>Analysis Complete</h2>
                    <div style={{ padding: '32px 0', borderTop: '1px solid var(--cv-border)', borderBottom: '1px solid var(--cv-border)', textAlign: 'center', marginBottom: '24px' }}>
                      <div className="summary-prob" style={{ fontSize: '84px' }}>
                        {result?.prediction?.probability != null ? (result.prediction.probability * 100).toFixed(1) : '--'}
                        <span style={{ fontSize: '42px', color: 'var(--cv-text-muted)', marginLeft: '4px' }}>%</span>
                      </div>
                      <div className="summary-label" style={{ marginTop: '12px' }}>Model Probability</div>
                    </div>
                    <div style={{ padding: '16px', background: 'var(--cv-surface)', borderRadius: '4px', fontSize: '13px', lineHeight: 1.5, borderLeft: '3px solid var(--cv-red)' }}>
                      <strong style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>Calibrated Risk Assessment</strong>
                      <div style={{ color: 'var(--cv-text-muted)' }}>Decision aids inform clinical judgment. See detailed attribution below.</div>
                    </div>
                    <div style={{ marginTop: '24px', textAlign: 'center' }}>
                      <a href="#result-section" className="nav-link" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--cv-red)', display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px', border: '1px solid rgba(158, 27, 46, 0.2)', borderRadius: '4px', transition: 'all 0.2s' }}>
                        View Detailed Attribution <span aria-hidden="true">&darr;</span>
                      </a>
                    </div>
                  </div>
                )}
              </div>
              {/* Clinical Use Notice Card */}
              <div className="summary-notice-card">
                <div className="summary-notice-quote">
                  &ldquo;A modelled probability is a decision aid, not a diagnosis &mdash; always confirm findings with a physician.&rdquo;
                </div>
                <div className="summary-notice-tag">CLINICAL USE NOTICE</div>
              </div>
            </div>

          </div>
        </section>

        {/* 5. FULL RESULT EXPERIENCE */}
        {result && !loading && (
          <section id="result-section" className="result-section">
            <div className="container result-container">
              <div>
                <h2 className="res-heading">Your model result</h2>
                <div className="res-prob-block">
                  <div className="res-prob-val">{result?.prediction?.probability != null ? (result.prediction.probability * 100).toFixed(1) : '--'}<span>%</span></div>
                  <div className="res-prob-lbl">Model Probability</div>
                </div>
              </div>
              
              <div>
                <div className="res-info">
                  Based on the provided cardiovascular profile, CardioVanta generated a <strong>{result?.prediction?.probability != null ? (result.prediction.probability * 100).toFixed(1) : '--'}%</strong> modelled probability estimate from the production inference pipeline.
                </div>
                <div className="res-threshold">
                  {result?.prediction?.threshold_status ? (
                    <strong>{result.prediction.threshold_status}</strong>
                  ) : (
                    "No validated production decision threshold is configured."
                  )}
                </div>

                {result?.development_range_warning?.outside_development_range && (
                  <div className="warning-alert">
                    <h4>Development Range Guardrail</h4>
                    <p>Features outside observed development-data range: {(result.development_range_warning.features || []).join(', ')}.</p>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* 6. SHAP EXPLANATION */}
        {result && !loading && result.shap_equivalent_explanation && (
          <section className="shap-explanation-section" style={{ paddingBottom: '40px', paddingTop: '40px' }}>
            <div className="container">
              <div className="exp-header" style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '32px', marginBottom: '16px' }}>Why the model responded this way</h2>
                <p style={{ fontSize: '16px', color: 'var(--cv-text-dark-2)', fontWeight: 500, padding: '16px', backgroundColor: '#F8F6F4', borderRadius: '8px' }}>
                  <strong>Important Notice:</strong> These are model-attribution signals, not medical causes or a diagnosis. They reflect how the mathematical model weighted each input relative to its baseline, and they do not imply certainty or serve as a treatment recommendation.
                </p>
              </div>
              {renderShapExplanation(result.shap_equivalent_explanation, result.prediction.probability)}
            </div>
          </section>
        )}

        {/* 7. EXISTING TECHNICAL EXPLANATION */}
        {result && !loading && result.explanation && (
          <section className="explanation-section" style={{ paddingBottom: '80px', paddingTop: '40px', borderTop: '1px solid #EAE3DC' }}>
            <div className="container">
              <div className="exp-header">
                <h2>Technical Audit (Logistic Regression)</h2>
                <p>{result.explanation.note || "These contributions describe how the standalone Logistic Regression explanation model moved the underlying log-odds for this prediction. They describe model behavior, not clinical causality."}</p>
              </div>
              {renderExplanation(result.explanation)}
            </div>
          </section>
        )}
      </main>

      {/* 9. FOOTER */}
      <footer className="footer" style={{ padding: '80px 0', backgroundColor: 'var(--cv-dark)', color: 'var(--cv-warm-white)' }}>
        <div className="container">
          <img src="/brand/cardiovanta-horizontal-transparent.png" alt="CardioVanta" className="footer-logo-img" style={{ filter: 'brightness(0) invert(1)' }} />
          <div className="footer-tagline" style={{ fontSize: '24px', fontFamily: 'var(--cv-font-display), serif', marginBottom: '24px' }}>Intelligent cardiovascular insight.</div>
          <p className="footer-disclaimer" style={{ fontSize: '14px', color: '#8C8279' }}>
            CardioVanta is a demonstration of machine learning techniques for educational and evaluation purposes. It is not a medical device and is not intended for diagnosis, treatment, or medical advice.
          </p>
          <div className="footer-copyright">
            &copy; 2026 CardioVanta
          </div>
        </div>
      </footer>
    </>
  );
}
