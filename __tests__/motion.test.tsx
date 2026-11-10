/**
 * The motion system: CSS and TypeScript tokens stay in sync, and the motion helpers never change
 * what a value means (only how it arrives).
 */
import fs from 'fs';
import path from 'path';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MotionGlobalConfig } from 'framer-motion';
import { DURATION, EASE, STAGGER, formatProbability } from '../src/lib/motion';
import { RouteTransition } from '../src/components/motion/RouteTransition';
import { AnimatedNumber } from '../src/components/motion/AnimatedNumber';

const css = fs.readFileSync(path.resolve(__dirname, '../src/app/globals.css'), 'utf-8');

function cssVar(name: string): string {
  const match = new RegExp(`${name}:\\s*([^;]+);`).exec(css);
  if (!match) throw new Error(`${name} is not defined in globals.css`);
  return match[1].trim();
}

describe('Motion tokens', () => {
  it.each([
    ['--cv-dur-press', DURATION.press],
    ['--cv-dur-fast', DURATION.fast],
    ['--cv-dur-base', DURATION.base],
    ['--cv-dur-slow', DURATION.slow],
    ['--cv-dur-reveal', DURATION.reveal],
    ['--cv-dur-count', DURATION.count],
    ['--cv-stagger', STAGGER.base],
    ['--cv-stagger-tight', STAGGER.tight],
  ])('%s matches the TypeScript token', (name, seconds) => {
    expect(cssVar(name)).toBe(`${Math.round(seconds * 1000)}ms`);
  });

  it.each([
    ['--cv-ease-out', EASE.out],
    ['--cv-ease-in-out', EASE.inOut],
    ['--cv-ease-in', EASE.in],
  ])('%s matches the TypeScript curve', (name, curve) => {
    expect(cssVar(name)).toBe(`cubic-bezier(${curve.join(', ')})`);
  });

  it('keeps the house curve the landing page has always used', () => {
    expect(EASE.out).toEqual([0.22, 1, 0.36, 1]);
  });

  it('turns movement off for people who ask for reduced motion', () => {
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    expect(css).toMatch(/::view-transition-new\(\*\)[\s\S]*animation: none !important/);
  });
});

describe('formatProbability', () => {
  it('prints exactly what the results panel has always printed', () => {
    for (const p of [0, 0.0004, 0.2984019984, 0.5, 0.85, 0.9999, 1]) {
      expect(formatProbability(p)).toBe((p * 100).toFixed(1));
    }
  });
});

describe('RouteTransition', () => {
  it('renders its children unchanged where React has no <ViewTransition> (as in Jest)', () => {
    render(
      <RouteTransition>
        <main>page content</main>
      </RouteTransition>
    );
    expect(screen.getByRole('main')).toHaveTextContent('page content');
  });
});

describe('AnimatedNumber', () => {
  const format = (n: number) => n.toFixed(1);

  afterEach(() => {
    MotionGlobalConfig.skipAnimations = false;
  });

  it('is hidden from assistive technology (the caller renders the exact value as text)', () => {
    const { container } = render(<AnimatedNumber value={29.840199845} format={format} />);
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
  });

  it('always lands on the exact formatted value', async () => {
    MotionGlobalConfig.skipAnimations = true;
    const { container } = render(<AnimatedNumber value={29.840199845} format={format} />);
    await waitFor(() => expect(container.firstChild).toHaveTextContent(/^29\.8$/));
  });
});
