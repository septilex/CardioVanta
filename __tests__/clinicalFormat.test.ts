/**
 * Plain-language estimate wording (src/lib/clinicalFormat.ts) and the JavaScript hoisting rules it relies on.
 *
 * The language examples run through `new Function(...)`, so they are evaluated by Node's own JavaScript engine
 * exactly as written, not after the test transpiler has rewritten `let`/`const`.
 */
import { NO_ESTIMATE, describeEstimate } from '../src/lib/clinicalFormat';

describe('describeEstimate', () => {
  it('words a probability as people out of 100', () => {
    expect(describeEstimate(0.1234)).toEqual({ percentText: '12.3', inHundred: 12, headline: 'About 12' });
    expect(describeEstimate(0.994343297)).toEqual({ percentText: '99.4', inHundred: 99, headline: 'About 99' });
  });

  it('says "Fewer than 1" instead of "About 0"', () => {
    expect(describeEstimate(0.0049)).toMatchObject({ inHundred: 0, headline: 'Fewer than 1', percentText: '0.5' });
  });

  it('clamps rounding to 0-100', () => {
    expect(describeEstimate(1).inHundred).toBe(100);
    expect(describeEstimate(0).inHundred).toBe(0);
  });

  it.each([null, undefined, Number.NaN, Number.POSITIVE_INFINITY])('shows placeholders for %p', (value) => {
    expect(describeEstimate(value)).toEqual({ percentText: '--', inHundred: null, headline: '--' });
  });
});

describe('Hoisting', () => {
  it('lets the module build NO_ESTIMATE from a function declared further down the file', () => {
    // NO_ESTIMATE is evaluated at import time, before the line that declares describeEstimate.
    expect(NO_ESTIMATE).toEqual({ percentText: '--', inHundred: null, headline: '--' });
    expect(Object.isFrozen(NO_ESTIMATE)).toBe(true);
  });

  it('makes a function declaration callable before its line', () => {
    const run = new Function(`
      "use strict";
      const result = headline(42);          // called before the declaration below
      function headline(n) { return "About " + n; }
      return result;
    `);
    expect(run()).toBe('About 42');
  });

  it('hoists a var declaration but not its value', () => {
    const run = new Function(`
      "use strict";
      const before = count;                 // already declared, not yet assigned
      var count = 3;
      return [before, count];
    `);
    expect(run()).toEqual([undefined, 3]);
  });

  it('throws for let and const read before their line (temporal dead zone)', () => {
    const readLet = new Function(`"use strict"; const value = limit; let limit = 100; return value;`);
    const callConstArrow = new Function(`
      "use strict";
      const text = headline(42);           // the binding exists but is not initialised yet
      const headline = (n) => "About " + n;
      return text;
    `);
    expect(() => readLet()).toThrow(ReferenceError);
    expect(() => callConstArrow()).toThrow(ReferenceError);
  });
});
