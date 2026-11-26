/**
 * React side effects (useEffect) in three real CardioVanta components:
 *
 * - AnimatedNumber (src/components/motion/AnimatedNumber.tsx): starts a count-up animation, restarts it when
 *   `value` changes, and stops it in cleanup. Dependencies: [value, format, delay, reduce].
 * - Landing header (src/app/page.tsx): subscribes to window "scroll" to style the header, unsubscribes in cleanup.
 *   Dependencies: [] (one subscription for the component's lifetime).
 * - DatabaseEvaluations (src/components/research/DatabaseEvaluations.tsx): fetches research data and aborts the
 *   request in cleanup, so a discarded effect never updates state. Dependencies: [].
 *
 * Each is also checked under React.StrictMode, which in development mounts, cleans up and re-mounts every effect.
 */
import React, { StrictMode } from 'react';
import { act, render, screen } from '@testing-library/react';
import { animate } from 'framer-motion';
import { AnimatedNumber } from '../src/components/motion/AnimatedNumber';
import LandingPage from '../src/app/page';
import { DatabaseEvaluations } from '../src/components/research/DatabaseEvaluations';
import { fetchResearchEvaluations, type ResearchEvaluations } from '../src/lib/api';

jest.mock('framer-motion', () => {
  const actual = jest.requireActual('framer-motion');
  return { ...actual, animate: jest.fn(actual.animate), useReducedMotion: () => false };
});
jest.mock('../src/lib/api', () => {
  const actual = jest.requireActual('../src/lib/api');
  return { ...actual, fetchResearchEvaluations: jest.fn() };
});

const mockAnimate = animate as jest.MockedFunction<typeof animate>;
const mockFetch = fetchResearchEvaluations as jest.MockedFunction<typeof fetchResearchEvaluations>;

/** Replace framer-motion's animate with a recorder: each call returns controls whose stop() is tracked. */
function recordAnimations() {
  const runs: { to: number; stop: jest.Mock }[] = [];
  mockAnimate.mockImplementation(((from: number, to: number) => {
    const stop = jest.fn();
    runs.push({ to, stop });
    return { stop } as unknown as ReturnType<typeof animate>;
  }) as unknown as typeof animate);
  return runs;
}

const format = (n: number) => n.toFixed(1);

describe('AnimatedNumber: effect with dependencies and cleanup', () => {
  afterEach(() => mockAnimate.mockReset());

  it('starts one animation after mount', () => {
    const runs = recordAnimations();
    render(<AnimatedNumber value={42} format={format} />);
    expect(runs.map((r) => r.to)).toEqual([42]);
  });

  it('does not restart when it re-renders with the same dependencies', () => {
    const runs = recordAnimations();
    const { rerender } = render(<AnimatedNumber value={42} format={format} />);
    rerender(<AnimatedNumber value={42} format={format} className="changed" />);   // className is not a dependency
    expect(runs).toHaveLength(1);
    expect(runs[0].stop).not.toHaveBeenCalled();
  });

  it('stops the old animation and starts a new one when a dependency changes', () => {
    const runs = recordAnimations();
    const { rerender } = render(<AnimatedNumber value={42} format={format} />);
    rerender(<AnimatedNumber value={7} format={format} />);
    expect(runs.map((r) => r.to)).toEqual([42, 7]);
    expect(runs[0].stop).toHaveBeenCalledTimes(1);        // cleanup of the previous effect
    expect(runs[1].stop).not.toHaveBeenCalled();
  });

  it('stops the running animation on unmount', () => {
    const runs = recordAnimations();
    const { unmount } = render(<AnimatedNumber value={42} format={format} />);
    unmount();
    expect(runs[0].stop).toHaveBeenCalledTimes(1);
  });

  it('leaves exactly one animation running under Strict Mode', () => {
    const runs = recordAnimations();
    render(<StrictMode><AnimatedNumber value={42} format={format} /></StrictMode>);
    const running = runs.filter((r) => r.stop.mock.calls.length === 0);
    expect(running).toHaveLength(1);
  });
});

describe('Landing header: one scroll subscription for the lifetime of the page', () => {
  let added: jest.SpyInstance;
  let removed: jest.SpyInstance;
  const scrollCalls = (spy: jest.SpyInstance) => spy.mock.calls.filter(([type]) => type === 'scroll');

  beforeEach(() => {
    mockAnimate.mockReset();
    added = jest.spyOn(window, 'addEventListener');
    removed = jest.spyOn(window, 'removeEventListener');
  });
  afterEach(() => {
    added.mockRestore();
    removed.mockRestore();
    Object.defineProperty(window, 'scrollY', { value: 0, configurable: true });
  });

  it('styles the header after scrolling past 60px', () => {
    const { container } = render(<LandingPage />);
    const header = container.querySelector('header.lp-header') as HTMLElement;
    expect(header).not.toHaveClass('lp-header--scrolled');
    act(() => {
      Object.defineProperty(window, 'scrollY', { value: 120, configurable: true });
      window.dispatchEvent(new Event('scroll'));
    });
    expect(header).toHaveClass('lp-header--scrolled');
  });

  it('removes the same listener it added when the page unmounts', () => {
    const { unmount } = render(<LandingPage />);
    const headerListener = scrollCalls(added).find(([, , options]) => options && (options as AddEventListenerOptions).passive)?.[1];
    expect(headerListener).toBeDefined();
    unmount();
    expect(scrollCalls(removed).map(([, listener]) => listener)).toContain(headerListener);
  });

  it('keeps no extra scroll listener after Strict Mode re-runs the effect', () => {
    const { unmount } = render(<StrictMode><LandingPage /></StrictMode>);
    const live = () => {
      const adds = scrollCalls(added).map(([, l]) => l);
      const removes = new Set(scrollCalls(removed).map(([, l]) => l));
      return adds.filter((l) => !removes.has(l));
    };
    const liveWhileMounted = live().length;
    unmount();
    expect(live()).toHaveLength(0);                       // every listener added was removed
    expect(liveWhileMounted).toBeGreaterThan(0);
  });
});

describe('DatabaseEvaluations: fetch with abort-on-cleanup and no stale updates', () => {
  const data = (label: string): ResearchEvaluations => ({
    evaluations: [{ version: label, serialization: 'joblib', cohort: 'c', cohort_name: `Cohort ${label}`, cohort_role: 'development',
      n_patients: 242, method: 'm', evaluated_on: '2026-11-01', source: 's', metric: 'roc_auc', value: 0.9 }],
    version_coverage: [],
    unevaluated_cohorts: [],
  });

  beforeEach(() => mockFetch.mockReset());

  it('requests once per mount and aborts the request on unmount', () => {
    const signals: AbortSignal[] = [];
    mockFetch.mockImplementation((s) => { signals.push(s as AbortSignal); return new Promise(() => {}); });
    const { rerender, unmount } = render(<DatabaseEvaluations />);
    rerender(<DatabaseEvaluations />);                     // a re-render does not re-run a [] effect
    expect(mockFetch).toHaveBeenCalledTimes(1);
    unmount();
    expect(signals[0].aborted).toBe(true);
  });

  it('under Strict Mode, ignores the discarded first request even if it answers last', async () => {
    const pending: { signal: AbortSignal; resolve: (d: ResearchEvaluations) => void }[] = [];
    mockFetch.mockImplementation((signal) => new Promise((resolve) => pending.push({ signal: signal as AbortSignal, resolve })));
    render(<StrictMode><DatabaseEvaluations /></StrictMode>);

    expect(pending).toHaveLength(2);                       // mount, cleanup, re-mount
    expect(pending[0].signal.aborted).toBe(true);          // the first effect was cleaned up
    expect(pending[1].signal.aborted).toBe(false);

    await act(async () => pending[1].resolve(data('current')));
    await act(async () => pending[0].resolve(data('stale')));   // a late answer from the discarded effect

    expect(screen.getByText(/Cohort current/)).toBeInTheDocument();
    expect(screen.queryByText(/Cohort stale/)).not.toBeInTheDocument();
  });
});
