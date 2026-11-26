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

  // V8's temporal-dead-zone message is "Cannot access 'x' before initialization". Checking it separates the TDZ
  // from the other ReferenceError, "x is not defined", which a misspelt or undeclared name would throw.
  const TDZ = /Cannot access '\w+' before initialization/;

  it('throws for let read before its line (temporal dead zone), unlike an undeclared name', () => {
    const readLet = new Function(`"use strict"; const value = limit; let limit = 100; return value;`);
    const readUndeclared = new Function(`"use strict"; return limitt;`);
    expect(() => readLet()).toThrow(ReferenceError);
    expect(() => readLet()).toThrow(TDZ);
    expect(() => readUndeclared()).toThrow(/limitt is not defined/);
  });

  it('throws for const read before its line, for values and for arrow functions alike', () => {
    const readConst = new Function(`"use strict"; const doubled = threshold * 2; const threshold = 0.5; return doubled;`);
    const callConstArrow = new Function(`
      "use strict";
      const text = headline(42);           // the binding exists but is not initialised yet
      const headline = (n) => "About " + n;
      return text;
    `);
    expect(() => readConst()).toThrow(TDZ);
    expect(() => callConstArrow()).toThrow(TDZ);
  });

  it('shows let is hoisted: the inner binding shadows the outer one before its line', () => {
    // If let were not hoisted, the read would find the outer "outer". It throws instead: the inner binding
    // already exists from the start of the block, uninitialised.
    const run = new Function(`
      "use strict";
      let label = "outer";
      {
        const seen = label;
        let label = "inner";
        return seen;
      }
    `);
    expect(() => run()).toThrow(TDZ);
  });

  it('ends the dead zone at the declaration: a later call through a closure works', () => {
    const run = new Function(`
      "use strict";
      const read = () => limit;            // refers to limit before its line, but does not read it yet
      let limit = 100;
      return read();                       // called after initialisation
    `);
    expect(run()).toBe(100);
  });

  it('gives typeof no exemption inside the dead zone', () => {
    const typeofUndeclared = new Function(`"use strict"; return typeof neverDeclared;`);
    const typeofInTdz = new Function(`"use strict"; const t = typeof later; let later = 1; return t;`);
    expect(typeofUndeclared()).toBe('undefined');
    expect(() => typeofInTdz()).toThrow(TDZ);
  });
});
