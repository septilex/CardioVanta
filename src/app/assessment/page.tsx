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
        <section className="workspace-section" style={{ paddingTop: '64px' }}>
          <div className="container workspace-grid">
            
            <div className="workspace-form-area">
              <div className="workspace-intro">
                <h1 style={{ fontSize: '40px', marginBottom: '16px', color: 'var(--cv-text-dark-1)' }}>Cardiovascular Assessment</h1>
                <p>Enter the available measurements below to generate a modelled probability estimate.</p>
                <div style={{ marginTop: '24px', fontSize: '12px', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--cv-red)', fontWeight: 600 }}>13 MODEL INPUTS</div>
              </div>

              <form onSubmit={handleSubmit}>
                {/* GROUP 01 */}
                <div className="form-group">
                  <div className="form-group-header">
                    <span>Patient Profile</span>
                    <span className="form-group-num">01</span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="age">
                        <span>Age</span>
                        <span className="input-code" aria-hidden="true">age</span>
                      </label>
                      <input className="input-control" type="number" id="age" name="age" value={formData.age} onChange={handleChange} required min="1" max="110" />
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
                    </div>
                  </div>
                </div>

                {/* GROUP 02 */}
                <div className="form-group">
                  <div className="form-group-header">
                    <span>Vitals &amp; Laboratory</span>
                    <span className="form-group-num">02</span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="trestbps">
                        <span>Resting Blood Pressure</span>
                        <span className="input-code" aria-hidden="true">trestbps</span>
                      </label>
                      <input className="input-control" type="number" id="trestbps" name="trestbps" value={formData.trestbps} onChange={handleChange} required />
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="chol">
                        <span>Serum Cholestoral (mg/dl)</span>
                        <span className="input-code" aria-hidden="true">chol</span>
                      </label>
                      <input className="input-control" type="number" id="chol" name="chol" value={formData.chol} onChange={handleChange} required />
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
                    </div>
                  </div>
                </div>

                {/* GROUP 03 */}
                <div className="form-group">
                  <div className="form-group-header">
                    <span>Exercise Response</span>
                    <span className="form-group-num">03</span>
                  </div>
                  <div className="fields-grid">
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="thalach">
                        <span>Maximum Heart Rate Achieved</span>
                        <span className="input-code" aria-hidden="true">thalach</span>
                      </label>
                      <input className="input-control" type="number" id="thalach" name="thalach" value={formData.thalach} onChange={handleChange} required />
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
                    </div>
                    <div className="input-wrapper">
                      <label className="input-label" htmlFor="oldpeak">
                        <span>ST Depression Induced by Exercise</span>
                        <span className="input-code" aria-hidden="true">oldpeak</span>
                      </label>
                      <input className="input-control" type="number" step="0.1" id="oldpeak" name="oldpeak" value={formData.oldpeak} onChange={handleChange} required />
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
                    </div>
                  </div>
                </div>

                {/* GROUP 04 */}
                <div className="form-group">
                  <div className="form-group-header">
                    <span>Diagnostic Markers</span>
                    <span className="form-group-num">04</span>
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
                    </div>
                  </div>
                </div>

                {error && <div style={{ color: '#D5495B', marginBottom: '24px', fontWeight: 500 }}>{error}</div>}
                
                <div style={{ display: 'flex', gap: '16px' }}>
                  <button type="submit" className="submit-btn" disabled={loading} style={{ flex: 1 }}>
                    {loading ? "Analyzing Profile..." : "Generate Analysis"}
                  </button>
                  <button type="button" onClick={handleReset} className="btn-secondary" style={{ padding: '20px 40px', fontSize: '18px' }}>
                    Reset
                  </button>
                </div>
              </form>
            </div>

            {/* Sticky Panel */}
            <div className="workspace-summary-area">
              <div className="sticky-summary">
                <div className="summary-header">Model Output</div>
                
                {!result && !loading && (
                  <div>
                    <div className="summary-status">Awaiting Input</div>
                    <div className="summary-desc">Complete the profile to generate a modelled probability.</div>
                  </div>
                )}
                
                {loading && (
                  <div>
                    <div className="summary-status" style={{color: '#C94A5B'}}>Processing...</div>
                    <div className="summary-desc">Evaluating cardiovascular markers via the prediction API.</div>
                  </div>
                )}

                {result && !loading && (
                  <div>
                    <div className="summary-status">Analysis Complete</div>
                    <div className="summary-prob">{result?.prediction?.probability != null ? (result.prediction.probability * 100).toFixed(1) : '--'}<sup>%</sup></div>
                    <div className="summary-label">Model Probability</div>
                  </div>
                )}
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
