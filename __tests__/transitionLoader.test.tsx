/**
 * The CardioVanta transition loader plays only when moving to Research or About (link click, keyboard,
 * back/forward, direct visit), never for Overview or Heart Analysis, never twice for one navigation,
 * and always leaves: on arrival, when the user goes elsewhere, or after the failsafe.
 */
import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import {
  LOADER_ROUTES,
  LOADER_TIMING,
  TransitionLoaderGate,
  loaderDestination,
} from '../src/components/loader/TransitionLoaderGate';

let mockPath = '/assessment';
const push = jest.fn();
const prefetch = jest.fn();
jest.mock('next/navigation', () => ({
  ...jest.requireActual('next/navigation'),
  usePathname: () => mockPath,
  useRouter: () => ({ push, prefetch, replace: jest.fn(), back: jest.fn(), forward: jest.fn(), refresh: jest.fn() }),
}));

// jsdom cannot navigate; stop links the gate lets through from trying.
const blockJsdomNavigation = (e: Event) => e.preventDefault();

// Plain anchors on purpose: the gate intercepts any same-origin link, not only next/link.
function App() {
  return (
    <>
      {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
      <a href="/">Overview</a>
      <a href="/assessment">Heart Analysis</a>
      <a href="/research">Research</a>
      <a href="/about">About</a>
      <a href="/research" target="_blank">Research (new tab)</a>
      <TransitionLoaderGate />
    </>
  );
}

const loader = () => screen.queryByRole('status');
const advance = (ms: number) => act(() => { jest.advanceTimersByTime(ms); });
const setReducedMotion = (on: boolean) => {
  window.matchMedia = jest.fn().mockImplementation((q: string) => ({
    matches: on && q.includes('reduce'),
    media: q,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    addListener: jest.fn(),
    removeListener: jest.fn(),
    onchange: null,
    dispatchEvent: jest.fn(),
  }));
};

/** Simulate the router committing a new route. */
function arrive(rerender: (ui: React.ReactElement) => void, path: string) {
  mockPath = path;
  act(() => rerender(<App />));
}

/** Run the rest of the sequence after arrival: complete + exit. */
function settle() {
  advance(LOADER_TIMING.minVisible + LOADER_TIMING.complete + LOADER_TIMING.exit + 50);
}

beforeEach(() => {
  jest.useFakeTimers();
  mockPath = '/assessment';
  push.mockClear();
  prefetch.mockClear();
  setReducedMotion(false);
  document.addEventListener('click', blockJsdomNavigation);
});
afterEach(() => {
  document.removeEventListener('click', blockJsdomNavigation);
  jest.useRealTimers();
  document.documentElement.removeAttribute('data-cv-reveal');
});

describe('which routes use the loader', () => {
  it('is limited to Research and About', () => {
    expect(Object.keys(LOADER_ROUTES).sort()).toEqual(['/about', '/research']);
    expect(loaderDestination('/research')).toBe('Research');
    expect(loaderDestination('/about/')).toBe('About');
    expect(loaderDestination('/')).toBeNull();
    expect(loaderDestination('/assessment')).toBeNull();
  });

  it.each(['Overview', 'Heart Analysis'])('does not appear for %s', (name) => {
    render(<App />);
    fireEvent.click(screen.getByRole('link', { name }));
    advance(500);
    expect(loader()).toBeNull();
    expect(push).not.toHaveBeenCalled();
  });

  it('leaves modified clicks and new-tab links to the browser', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'Research' }), { ctrlKey: true });
    fireEvent.click(screen.getByRole('link', { name: 'Research (new tab)' }));
    advance(500);
    expect(loader()).toBeNull();
    expect(push).not.toHaveBeenCalled();
  });
});

describe('navigating by link', () => {
  it('covers the page first, then navigates, then reveals the page once it has arrived', () => {
    const { rerender } = render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'Research' }));

    expect(loader()).toHaveTextContent('Loading Research');
    expect(prefetch).toHaveBeenCalledWith('/research');
    expect(push).not.toHaveBeenCalled(); // the loader covers the old page before the route changes
    advance(LOADER_TIMING.pushDelay);
    expect(push).toHaveBeenCalledWith('/research');

    // Still waiting for the route: the loader stays (no blank page), however long the bar has run.
    advance(LOADER_TIMING.minVisible + 1000);
    expect(loader()).toBeInTheDocument();
    expect(loader()).toHaveAttribute('data-phase', 'enter');

    arrive(rerender, '/research');
    expect(loader()).toHaveAttribute('data-phase', 'complete');
    advance(LOADER_TIMING.complete);
    expect(loader()).toHaveAttribute('data-phase', 'exit');
    expect(document.documentElement).toHaveAttribute('data-cv-reveal');
    advance(LOADER_TIMING.exit);
    expect(loader()).toBeNull();
    advance(LOADER_TIMING.reveal);
    expect(document.documentElement).not.toHaveAttribute('data-cv-reveal');
  });

  it('works for Research -> About -> Research, every time', () => {
    const { rerender } = render(<App />);
    for (const [name, path] of [['Research', '/research'], ['About', '/about'], ['Research', '/research']] as const) {
      fireEvent.click(screen.getByRole('link', { name }));
      expect(loader()).toHaveTextContent(`Loading ${name}`);
      advance(LOADER_TIMING.pushDelay);
      arrive(rerender, path);
      settle();
      expect(loader()).toBeNull();
    }
    expect(push.mock.calls.map((c) => c[0])).toEqual(['/research', '/about', '/research']);
  });

  it('ignores repeated clicks while a navigation is under way', () => {
    render(<App />);
    const link = screen.getByRole('link', { name: 'About' });
    fireEvent.click(link);
    fireEvent.click(link);
    advance(100);
    fireEvent.click(link);
    advance(LOADER_TIMING.pushDelay);
    expect(push).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole('status')).toHaveLength(1);
  });

  it('does nothing special for a link to the page already shown', () => {
    mockPath = '/research';
    window.history.pushState({}, '', '/research');
    render(<App />);
    settle(); // direct-visit loader finishes
    fireEvent.click(screen.getByRole('link', { name: 'Research' }));
    advance(500);
    expect(loader()).toBeNull();
    expect(push).not.toHaveBeenCalled();
    window.history.pushState({}, '', '/');
  });

  it('never stays up: leaves after the failsafe even if the route never arrives', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'Research' }));
    advance(LOADER_TIMING.failsafe);
    expect(loader()).toHaveAttribute('data-phase', 'exit');
    advance(LOADER_TIMING.exit);
    expect(loader()).toBeNull();
  });

  it('gets out of the way if the user goes to a page without the loader mid-run', () => {
    const { rerender } = render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'About' }));
    advance(300);
    arrive(rerender, '/'); // e.g. Back pressed before About arrived
    expect(loader()).toHaveAttribute('data-phase', 'exit');
    advance(LOADER_TIMING.exit);
    expect(loader()).toBeNull();
  });
});

describe('back, forward and direct visits', () => {
  it('plays when Back or Forward lands on Research or About', () => {
    const { rerender } = render(<App />);
    arrive(rerender, '/about'); // popstate: no click, the route is simply here
    expect(loader()).toHaveTextContent('Loading About');
    expect(push).not.toHaveBeenCalled(); // nothing to push, the page is already there
    settle();
    expect(loader()).toBeNull();

    arrive(rerender, '/assessment');
    expect(loader()).toBeNull();
  });

  it('is part of the first render on a direct visit, then leaves', () => {
    mockPath = '/research';
    render(<App />);
    expect(loader()).toHaveAttribute('data-initial', 'true');
    expect(loader()).toHaveTextContent('Loading Research');
    settle();
    expect(loader()).toBeNull();
  });

  it('renders nothing on a direct visit to other pages', () => {
    mockPath = '/';
    render(<App />);
    expect(loader()).toBeNull();
  });
});

describe('reduced motion', () => {
  it('runs a much shorter sequence', () => {
    setReducedMotion(true);
    const { rerender } = render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'About' }));
    advance(LOADER_TIMING.pushDelay);
    arrive(rerender, '/about');
    advance(LOADER_TIMING.minVisibleReduced + LOADER_TIMING.completeReduced + LOADER_TIMING.exitReduced + 20);
    expect(loader()).toBeNull();
    expect(LOADER_TIMING.minVisibleReduced + LOADER_TIMING.completeReduced + LOADER_TIMING.exitReduced).toBeLessThan(1000);
  });
});
