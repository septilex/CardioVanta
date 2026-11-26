"use client";
import { useEffect, useRef, useState } from 'react';
import type { PredictResponse } from '../../types';
import { aiEnabled, explainResult, type AIResponse } from '../../lib/aiExplanation';

export default function AIExplanation({ result }: { result: PredictResponse }) {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [content, setContent] = useState<AIResponse | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const c = new AbortController();
    setContent(null); setError(false); setLoading(false); setEnabled(false);
    aiEnabled(c.signal).then(v => { if (!c.signal.aborted) setEnabled(v && Boolean(result.explanation_token)); }).catch(() => {});
    return () => { c.abort(); active.current?.abort(); active.current = null; };
  }, [result]);
  async function explain() {
    if (active.current) return;
    const c = new AbortController(); active.current = c;
    setLoading(true); setError(false);
    const timer = setTimeout(() => c.abort(), 30000);
    try {
      const value = await explainResult(result, c.signal);
      if (active.current === c && !c.signal.aborted) setContent(value);
    } catch { if (active.current === c) setError(true); }
    finally { clearTimeout(timer); if (active.current === c) { active.current = null; setLoading(false); } }
  }
  return <section aria-label="AI explanation">
    <h3>AI-generated educational explanation</h3>
    <p>Optional: sends your model probability and feature contribution directions to OpenAI. These are sensitive health information. No raw clinical values or identifiers are sent.</p>
    <p>Not a diagnosis or a substitute for professional medical advice.</p>
    {!enabled && <p>AI explanations are currently unavailable.</p>}
    {!content && <button type="button" disabled={!enabled || loading} onClick={explain}>{error ? 'Retry AI explanation' : 'Explain my results in simple language'}</button>}
    {loading && <p role="status">Generating explanation…</p>}
    {error && <p role="alert">AI explanation failed. Your original prediction is unchanged. You can retry transient failures within three total attempts; generate a new prediction if this result has expired or used all attempts.</p>}
    {content && <div><p>{content.summary}</p><p>{content.prediction_interpretation}</p>
      <ul>{content.contributing_factors.map(f => <li key={f.feature_name}>{f.feature_name} ({f.contribution_direction}): {f.plain_language_explanation}</li>)}</ul>
      <h4>Limitations</h4><ul>{content.limitations.map((text, i) => <li key={i}>{text}</li>)}</ul>
      <p>{content.recommended_next_step}</p><p>{content.disclaimer}</p><small>{content.prompt_version}</small>
    </div>}
  </section>;
}
